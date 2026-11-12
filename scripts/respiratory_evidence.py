"""Offline section plan + guarded read-only context evidence for respiratory-system job."""
import json
import shutil
from pathlib import Path

import mwparserfromhell as mw

from mgwiki_editor.core import Wiki, now, read_json, write_json

JOB = Path('runs/biology-health-20261110/respiratory-system')
PLAN = [
    ('00-lead', 1, 26),
    ('01-anatomy', 27, 41),
    ('02-volumes', 42, 60),
    ('03-mechanics', 61, 127),
    ('04-gas-exchange', 128, 159),
    ('05-control', 160, 169),
    ('06-low-pressure', 170, 186),
    ('07-other-functions', 187, 215),
    ('08-clinical', 216, 229),
    ('09-exceptional-mammals', 230, 254),
    ('10-birds', 255, 281),
    ('11-reptiles-amphibians', 282, 303),
    ('12-fish', 304, 318),
    ('13-invertebrates', 319, 347),
    ('14-plants', 348, 363),
    ('15-external', 364, 396),
]


def local_plan():
    source = (JOB / 'source.wiki').read_text(encoding='utf-8')
    lines = source.splitlines(keepends=True)
    assert ''.join(''.join(lines[t[1] - 1:t[2]]) for t in PLAN) == source, 'ranges incomplete'
    records = []
    for ident, start, end in PLAN:
        d = JOB / 'sections' / ident
        d.mkdir(parents=True, exist_ok=True)
        (d / 'source.wiki').write_text(''.join(lines[start - 1:end]), encoding='utf-8')
        records.append(dict(id=ident, start=start, end=min(end, len(lines)),
                            directory=str(d.relative_to(JOB)), status='pending',
                            heading=ident))
    write_json(JOB / 'section-plan.json', records)
    write_json(JOB / 'section-inputs.json', {
        'schema': 1,
        'artifacts': {name: __import__('hashlib').sha256((JOB / name).read_bytes()).hexdigest()
                      for name in ('source.wiki', 'job.json', 'existing.wiki', 'sandbox.wiki')},
    })
    # shared named-reference definitions
    code = mw.parse(source)
    refs = []
    for tag in code.filter_tags():
        if str(tag.tag) == 'ref' and tag.has('name') and not tag.self_closing:
            refs.append(str(tag))
    (JOB / 'shared-references.wiki').write_text('\n\n'.join(refs), encoding='utf-8')
    if not (JOB / 'country-names.json').exists():
        shutil.copyfile('data/country-names.json', JOB / 'country-names.json')
    # link/image inventory from source markup
    targets = set()
    for link in code.filter_wikilinks():
        t = str(link.title).strip()
        if ':' in t.split('#')[0]:
            continue
        targets.add(t.split('#')[0].replace('_', ' ').strip())
    for tmpl in code.filter_templates():
        name = str(tmpl.name).strip().lower()
        if name in {'main', 'see also', 'annotated link'} and tmpl.params:
            targets.add(str(tmpl.params[0].value).strip())
    write_json(JOB / 'source-link-inventory.json', sorted(targets))
    files = set()
    for link in code.filter_wikilinks():
        t = str(link.title)
        if t.lower().startswith(('file:', 'image:')):
            files.add(t.split(':', 1)[1].strip())
    for tmpl in code.filter_templates():
        for p in tmpl.params:
            if str(p.name).strip().lower() in {'image', 'image1', 'image2'} and str(p.value).strip():
                files.add(str(p.value).strip())
    write_json(JOB / 'source-image-inventory.json', sorted(files))
    print(f'plan: {len(records)} sections; links {len(targets)}; files {len(files)}; refs {len(refs)}')
    return sorted(targets), sorted(files)


def remote_evidence():
    wiki = Wiki()
    d = JOB / 'evidence'
    d.mkdir(exist_ok=True)
    targets = read_json(JOB / 'source-link-inventory.json')
    mapping = {}
    for start in range(0, len(targets), 45):
        p = d / f'links-{start:03}.json'
        if not p.exists():
            data = wiki.site('en').simple_request(
                action='query', prop='langlinks', titles='|'.join(targets[start:start + 45]),
                lllang='mg', lllimit='max', formatversion=2).submit()
            write_json(p, dict(retrieved_at=now(), response=data))
        data = read_json(p)['response']
        if 'continue' in data:
            raise SystemExit('unprocessed langlink continuation')
        for page in data['query']['pages']:
            ll = page.get('langlinks') or []
            mapping[page['title']] = dict(mg=ll[0]['title'] if ll else None,
                                          missing=page.get('missing', False),
                                          evidence_file=str(p.relative_to(JOB)))
        for n in data['query'].get('normalized', []):
            if n['to'] in mapping:
                mapping[n['from']] = mapping[n['to']]
    write_json(JOB / 'link-map.json', mapping)

    templates = ['Cite book', 'Cite journal', 'Cite web', 'Reflist', 'Main', 'See also',
                 'Multiple image', 'Infobox anatomy', 'Annotated link', 'Wikibooks',
                 'Authority control', 'Library resources box', 'Excerpt', 'Webarchive',
                 'Cn', 'Citation needed', 'Short description', 'About', 'Pp-vandalism']
    p = d / 'templates-mg.json'
    if not p.exists():
        data = wiki.site('mg').simple_request(
            action='query', titles='|'.join('Template:' + t for t in templates),
            prop='info', formatversion=2).submit()
        write_json(p, dict(retrieved_at=now(), response=data))
    tmpl_map = {page['title']: not page.get('missing', False)
                for page in read_json(p)['response']['query']['pages']}
    write_json(JOB / 'template-map.json', tmpl_map)

    cats = ['Sokajy:Biolojia', 'Sokajy:Anatomia', 'Sokajy:Fiziolojia',
            'Sokajy:Fahasalamana', 'Sokajy:Zavamaniry', 'Sokajy:Biby']
    p = d / 'categories-mg.json'
    if not p.exists():
        data = wiki.site('mg').simple_request(
            action='query', titles='|'.join(cats), prop='categoryinfo',
            formatversion=2).submit()
        write_json(p, dict(retrieved_at=now(), response=data))
    cat_map = {page['title']: not page.get('missing', False)
               for page in read_json(p)['response']['query']['pages']}
    write_json(JOB / 'category-map.json', cat_map)

    files = read_json(JOB / 'source-image-inventory.json')
    for start in range(0, len(files), 45):
        p = d / f'files-{start:03}.json'
        if not p.exists():
            data = wiki.site('en').simple_request(
                action='query', prop='imageinfo',
                titles='|'.join('File:' + f for f in files[start:start + 45]),
                iiprop='timestamp|extmetadata|url', formatversion=2).submit()
            write_json(p, dict(retrieved_at=now(), response=data))
    print('remote evidence done:', len(mapping), 'link rows;', len(tmpl_map), 'templates;',
          len(cat_map), 'categories')


if __name__ == '__main__':
    local_plan()
    remote_evidence()
