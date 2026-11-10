"""One serialized guarded metadata/dictionary worker; reuse every pinned response."""
import re
from pathlib import Path

import mwparserfromhell as mw

from mgwiki_editor.core import GuardError, Wiki, lookup, now, read_json, write_json

JOB = Path('runs/earthquake-20261108')
TERMS = [
    ('earthquake', 'horohoron-tany'), ('lithosphere', 'litôsfera'),
    ('seismic wave', 'onja'), ('fault', 'vaky'), ('stress', 'fihenjanana'),
    ('strain', "fiovan' endrika"), ('elastic', 'elastika'),
    ('magnitude', 'magnitioda'), ('intensity', 'hamafiny'),
    ('hypocenter', 'foibe'), ('epicenter', 'ivon-toerana'),
    ('normal fault', 'midina'), ('reverse fault', 'miakatra'),
    ('strike-slip fault', 'mitsivalana'), ('subduction', 'filentehana'),
    ('aftershock', 'horohoron-tany'), ('foreshock', 'horohoron-tany'),
    ('earthquake swarm', 'andiana'), ('pore pressure', 'tsindry'),
    ('supershear', 'haingana'), ('soil liquefaction', 'ranoka'),
    ('seismic moment', 'môma'), ('seismometer', 'seismômetatra'),
    ('tsunami', 'tsonamy'), ('asperity', 'marokoroko'),
    ('fracking', 'fanapotehana'), ('loess', 'lesy'), ('yaodong', 'fonenana'),
    ('olivine', 'ôlivina'), ('spinel', 'spinely'), ('phase transition', 'fiovana'),
    ('mantle', 'mantô'), ('crust', 'hoditra'), ('rigidity', 'hamafy'),
    ('shear wave', 'onja'), ('longitudinal wave', 'onja'),
    ('prediction', 'faminaniana'), ('forecasting', 'vinavina'),
    ('seismic retrofitting', 'fanamafisana'), ('expert system', 'rafitra'),
    ('panic attack', 'tahotra'), ('depression', 'fahaketrahana'),
    ('tidal force', 'samonta'), ('landslide', 'fihotsahana'),
    ('granular', 'voany'), ('neutron star', 'kintana'),
]


def main():
    e = JOB/'evidence'
    e.mkdir(exist_ok=True)
    code = mw.parse((JOB/'source.wiki').read_text(encoding='utf-8'))
    inventory = [{'target': str(x.title).strip(), 'label': str(x.text or x.title)}
                 for x in code.filter_wikilinks()]
    for t in code.filter_templates():
        name = str(t.name).strip().lower()
        if name in {'main', 'further', 'annotated link'}:
            for p in t.params:
                if str(p.name).strip().isdigit():
                    inventory.append({'target': str(p.value).strip(), 'label': str(p.value).strip()})
    write_json(JOB/'source-link-inventory.json', inventory)
    extras = ['China', 'Chile', 'United States', 'Canada', 'Mexico', 'Peru',
              'Philippines', 'Tajikistan', 'Turkey', 'Japan', 'Haiti', 'Mars', 'Moon',
              'Sun', 'Milky Way']
    targets = sorted({x['target'].split('#')[0].replace('_', ' ') for x in inventory
                      if ':' not in x['target'] and x['target']} | set(extras))
    files = sorted({x['target'].split(':', 1)[1].strip() for x in inventory
                    if x['target'].lower().startswith(('file:', 'image:'))})
    write_json(JOB/'source-file-inventory.json', files)
    wiki = Wiki()
    mapping = {}
    for start in range(0, len(targets), 45):
        output = e/f'links-{start:03d}.json'
        if not output.exists():
            response = wiki.site('en').simple_request(
                action='query', prop='langlinks', titles='|'.join(targets[start:start+45]),
                lllang='mg', lllimit='max', formatversion=2, redirects=1,
            ).submit()
            write_json(output, {'retrieved_at': now(), 'response': response})
            if 'continue' in response:
                raise GuardError('Required metadata continuation; preserve evidence.')
        data = read_json(output)['response']
        for page in data['query']['pages']:
            mapping[page['title']] = {'mg': page.get('langlinks', [{}])[0].get('title'),
                                     'missing': page.get('missing', False),
                                     'evidence_file': str(output.relative_to(JOB))}
        changes = data['query'].get('redirects', []) + data['query'].get('normalized', [])
        for _ in range(len(changes)+1):
            for item in changes:
                if item['to'] in mapping:
                    mapping[item['from']] = mapping[item['to']]
    write_json(JOB/'link-map.json', mapping)
    for filename, lang, params in [
        ('files.json', 'en', dict(prop='imageinfo', titles='|'.join('File:'+x for x in files),
                                 iiprop='timestamp|extmetadata')),
        ('categories.json', 'mg', dict(prop='info', titles='Sokajy:Horohoron-tany|Sokajy:Jeôlôjia|Sokajy:Loza voajanahary|Sokajy:Seismôlôjia')),
    ]:
        output = e/filename
        if not output.exists():
            response = wiki.site(lang).simple_request(action='query', formatversion=2, **params).submit()
            write_json(output, {'retrieved_at': now(), 'response': response})
    local = sorted({v['mg'] for v in mapping.values() if v.get('mg')})
    for start in range(0, len(local), 45):
        output = e/f'local-{start:03d}.json'
        if not output.exists():
            response = wiki.site('mg').simple_request(
                action='query', prop='info|extracts', titles='|'.join(local[start:start+45]),
                exintro=1, explaintext=1, exsentences=2, formatversion=2,
            ).submit()
            write_json(output, {'retrieved_at': now(), 'response': response})
    for english, malagasy in TERMS:
        for edition, word in [('en', english), ('mg', malagasy)]:
            output = e/f'lookup-{edition}-{re.sub(r"[^a-z0-9]+", "-", english)}.json'
            if output.exists():
                continue
            # Reuse duplicate same-sense candidate requests within this job.
            existing = next((f for f in e.glob('lookup-*.json')
                             if (read_json(f).get('edition'), read_json(f).get('word')) == (edition, word)), None)
            if existing:
                write_json(output, read_json(existing))
                continue
            try:
                result = lookup(edition, word)
            except GuardError as exc:
                if any(x in str(exc).lower() for x in ('cooldown', 'deferred', 'circuit', 'rate', 'overload')):
                    raise
                result = {'status': 'failed', 'edition': edition, 'word': word,
                          'retrieved_at': now(), 'error': str(exc)}
            write_json(output, result)
    print('Evidence complete:', len(targets), 'topics;', len(files), 'files;', len(TERMS), 'term pairs')


if __name__ == '__main__':
    main()
