"""Sequential, resumable evidence collection for the Oedipus translation."""
import json
import shutil
from pathlib import Path

import mwparserfromhell as mw

from mgwiki_editor.core import GuardError, Wiki, lookup, now, write_json

JOB = Path('runs/oedipus-20261105')


def main():
    evidence = JOB / 'evidence'
    evidence.mkdir(exist_ok=True)
    wiki = Wiki()
    output = evidence / 'family-template.json'
    if not output.exists():
        response = wiki.site('en').simple_request(
            action='query', prop='revisions', titles='Template:Family tree of the Theban royal house',
            rvprop='ids|content', rvslots='main', formatversion=2,
        ).submit()
        write_json(output, {'retrieved_at': now(), 'response': response})
    family = json.loads(output.read_text())['response']['query']['pages'][0]['revisions'][0]['slots']['main']['content']
    (evidence / 'family-template.wiki').write_text(family, encoding='utf-8')
    source = (JOB / 'source.wiki').read_text(encoding='utf-8')
    inventory = [{'target': str(x.title), 'label': str(x.text or x.title)}
                 for x in mw.parse(source + '\n' + family).filter_wikilinks()]
    write_json(JOB / 'source-link-inventory.json', inventory)
    targets = sorted({x['target'].split('#')[0].replace('_', ' ') for x in inventory
                      if ':' not in x['target'] and x['target']})
    files = sorted({x['target'].split(':', 1)[1].strip() for x in inventory
                    if x['target'].lower().startswith(('file:', 'image:'))}
                   | {'Oedipus and Sphinx, pelike, 450-440 BC, Berlin F 2355, 141646.jpg'})
    mapping = {}
    for start in range(0, len(targets), 45):
        output = evidence / f'links-{start:03d}.json'
        if not output.exists():
            response = wiki.site('en').simple_request(
                action='query', prop='langlinks', titles='|'.join(targets[start:start+45]),
                lllang='mg', lllimit='max', formatversion=2,
            ).submit()
            write_json(output, {'retrieved_at': now(), 'response': response})
            if 'continue' in response:
                raise GuardError('Link evidence requires continuation; preserved')
        data = json.loads(output.read_text())['response']
        for page in data['query']['pages']:
            mapping[page['title']] = {'mg': page.get('langlinks', [{}])[0].get('title'),
                                     'missing': page.get('missing', False),
                                     'evidence_file': str(output.relative_to(JOB))}
        for item in data.get('query', {}).get('normalized', []):
            if item['to'] in mapping:
                mapping[item['from']] = mapping[item['to']]
    write_json(JOB / 'link-map.json', mapping)
    for filename, lang, params in [
        ('files.json', 'en', dict(prop='imageinfo', titles='|'.join('File:'+x for x in files),
                                 iiprop='timestamp|extmetadata')),
        ('local-categories.json', 'mg', dict(prop='info', titles='Sokajy:Biôgrafia|Sokajy:Angano grika|Sokajy:Fedrà grika')),
    ]:
        output = evidence / filename
        if not output.exists():
            response = wiki.site(lang).simple_request(action='query', formatversion=2, **params).submit()
            write_json(output, {'retrieved_at': now(), 'response': response})
    shutil.copyfile('data/country-names.json', JOB / 'country-names.json')
    for english, malagasy in [('tragic hero', 'mahery fo'), ('oracle', 'mpaminany'),
                              ('incest', 'firaisana'), ('neurosis', 'nevrôzy'),
                              ('Oedipus complex', 'Oedipus'), ('infertility', 'tsy fiterahana'),
                              ('satyr', 'satira'), ('hubris', 'avonavona'),
                              ('folkloristics', 'angano'), ('patronymic', 'anarana')]:
        for edition, word in [('en', english), ('mg', malagasy)]:
            output = evidence / f'lookup-{edition}-{english.replace(" ", "-")}.json'
            if output.exists():
                continue
            try:
                result = lookup(edition, word)
            except GuardError as exc:
                result = {'status': 'failed', 'edition': edition, 'word': word,
                          'retrieved_at': now(), 'error': str(exc)}
            write_json(output, result)
    print('Pinned evidence:', len(targets), 'topics;', len(files), 'images')


if __name__ == '__main__':
    main()
