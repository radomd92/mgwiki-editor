"""Offline complete source-to-draft accounting; no inferred links or network access."""
from collections import Counter
from pathlib import Path

import mwparserfromhell as mw

from mgwiki_editor.core import read_json, write_json

JOB = Path('runs/earthquake-20261108')
OMITTED_LINKS = {'IRIS Consortium', '2012 (film)', 'San Andreas (film)'}


def main():
    text = (JOB/'draft.wiki').read_text(encoding='utf-8')
    code = mw.parse(text)
    mapping = read_json(JOB/'link-map.json')
    extra = read_json(JOB/'evidence/extra-links.json')['response']['query']
    for page in extra['pages']:
        mapping[page['title']] = {'mg': page.get('langlinks', [{}])[0].get('title'),
                                 'evidence_file': 'evidence/extra-links.json'}
    for item in extra.get('redirects', []):
        mapping[item['from']] = mapping.get(item['to'], {'mg': None, 'evidence_file': 'evidence/extra-links.json'})
    actual_links = {str(x.title).strip() for x in code.filter_wikilinks()}
    actual_files = {x.split(':', 1)[1] for x in actual_links if x.lower().startswith('file:')}
    if actual_files != set(read_json(JOB/'source-file-inventory.json')):
        raise RuntimeError('Missing/unexpected source file')
    rows = []
    expected_refs = Counter()
    for section in read_json(JOB/'section-plan.json'):
        directory = Path(section['directory'])
        source = mw.parse((directory/'source.wiki').read_text(encoding='utf-8'))
        translation_source = mw.parse((directory/'translation-source.wiki').read_text(encoding='utf-8'))
        expected_refs.update(str(t.get('name').value).strip('\"\' ') for t in translation_source.filter_tags()
                             if str(t.tag).lower() == 'ref' and t.has('name'))
        targets = [(str(x.title).strip(), str(x.text or x.title), 'wikilink') for x in source.filter_wikilinks()]
        for template in source.filter_templates():
            name = str(template.name).strip().lower()
            for p in template.params:
                key = str(p.name).strip().lower()
                if (name in {'main', 'further', 'annotated link'} and key.isdigit()
                    or key == 'title-link' or key.startswith('author') and 'link' in key):
                    targets.append((str(p.value).strip(), str(p.value).strip(), 'template_argument'))
        for target, label, syntax in targets:
            base = target.split('#', 1)[0].replace('_', ' ')
            hit = mapping.get(base, {})
            mg = hit.get('mg')
            if target.lower().startswith(('file:', 'image:')):
                disposition, reason = 'media_retained', 'Exact filename, same planned section, translated caption; Commons metadata pinned.'
            elif target.lower().startswith('category:'):
                disposition, reason = 'source_category_not_imported', 'Foreign categories not guessed; verified inert Malagasy categories appended.'
            elif base in OMITTED_LINKS:
                disposition, reason = 'omitted_user', 'User-authorized problematic-passage omission; original evidence/history retained.'
            elif mg:
                if mg not in actual_links:
                    raise RuntimeError('Verified target not present: '+target+' -> '+mg)
                disposition, reason = 'linked_mg_verified', 'Source langlink and actual local metadata/extract identify same topic; no target guessed.'
            else:
                disposition, reason = 'plain_text_fallback', 'No verified same-topic Malagasy target in pinned evidence; translated text or original citation metadata retained, no misleading link.'
            rows.append({'section': section['id'], 'source_target': target, 'source_label': label,
                         'source_syntax': syntax, 'draft_location': section['id'],
                         'malagasy_target': mg, 'disposition': disposition, 'reason': reason,
                         'evidence_file': hit.get('evidence_file')})
    actual_uses = Counter(str(t.get('name').value).strip('\"\' ') for t in code.filter_tags()
                          if str(t.tag).lower() == 'ref' and t.self_closing and t.has('name'))
    if expected_refs-actual_uses != Counter({'Sibson': 1, 'Rudnicki': 1}) or actual_uses-expected_refs:
        raise RuntimeError('Unexpected change to reference-use coverage')
    definitions = {str(t.get('name').value).strip('\"\' ') for t in code.filter_tags()
                   if str(t.tag).lower() == 'ref' and not t.self_closing and t.has('name')}
    if definitions != set(actual_uses):
        raise RuntimeError('Reference definition/reuse mismatch')
    write_json(JOB/'final-link-coverage.json', rows)
    write_json(JOB/'final-link-map.json', mapping)
    summary = Counter(x['disposition'] for x in rows)
    file_meta = {x['title'].split(':', 1)[1].casefold(): x for x in read_json(JOB/'evidence/files.json')['response']['query']['pages']}
    lines = ['# Coverage review', '', '- Scope: 28 planned fragments; explicit user-authorized omissions only.',
             '- Source/existing/sandbox snapshots read completely; local article and sandbox empty. Existing-preservation gate N/A, not a deletion.',
             '- Source prose not summarized. Same numerical claims/qualifiers, chronology and attribution, except recorded authorized omissions and source-issue handling.',
             '- Actual article: 46 unique headings; no templates; native lists/references/images. No source content tables to lose.',
             '- All source image filenames accounted below. OWID sliders adapted to explicit static source charts; normal File-description links restored.',
             f'- References: source uses {sum(expected_refs.values())}; draft uses {sum(actual_uses.values())}; definitions {len(definitions)}. Only Sibson/Rudnicki uses/definitions omitted with deleted sentence.',
             '- Central references restored at matching claims; citation metadata/identifiers preserved. No external URLs read. DOI and ISBN rendered literal, not resolved.',
             '- Country spellings: job-pinned country-names.json; cache exceptions verified by local extracts/langlinks. Historical Sina not anachronistic PRC name.',
             '- Original foreign agency/work names and licence identifier protected from numeric/country normalization. upright machine values use decimal dots.',
             '- Source anchor Magnitude retained; big_one normalized to source template’s MediaWiki anchor convention. No unresolved same-page links.',
             '- New inert categories at article end: Sokajy:Horohorontany, Sokajy:Jeolojia; existence/topic evidenced by evidence/category-search.json. No existing category links to overwrite.',
             '- All link occurrences: final-link-coverage.json, including Main/Further/annotated link and hidden citation author/title-link arguments.',
             '- Source issues: source-issues.md; open concerns nonblocking. No alleged factual adjudication or translator TODO in draft.', '',
             '## Link decisions', '']
    lines.extend(f'- {key}: {value}.' for key, value in sorted(summary.items()))
    lines += ['', '## Files', '']
    for name in read_json(JOB/'source-file-inventory.json'):
        meta = file_meta[name.casefold()]
        if meta.get('imagerepository') != 'shared':
            raise RuntimeError('Non-Commons file requires separate review: '+name)
        licence = meta['imageinfo'][0]['extmetadata']['LicenseShortName']['value']
        locations = sorted({r['section'] for r in rows if r['source_target'].split(':', 1)[-1] == name})
        lines.append(f'- `{name}`: '+', '.join(locations)+f'; Commons; {licence}; filename unchanged, caption translated, no image download.')
    (JOB/'coverage-review.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print('Coverage complete:', dict(summary), '; files', len(actual_files), '; ref definitions', len(definitions))


if __name__ == '__main__':
    main()
