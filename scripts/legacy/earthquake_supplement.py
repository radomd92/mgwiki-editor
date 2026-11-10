"""Sequential follow-up evidence, run only after the main evidence worker ends."""
from pathlib import Path

import mwparserfromhell as mw

from mgwiki_editor.core import Wiki, now, write_json

JOB = Path('runs/earthquake-20261108')


def main():
    w = Wiki()
    code = mw.parse((JOB/'source.wiki').read_text(encoding='utf-8'))
    targets = {'Aftershock: Earthquake in New York', 'Matthew 27:51', 'Matthew 28:2'}
    for t in code.filter_templates():
        for p in t.params:
            key = str(p.name).strip().lower()
            if key.startswith('author') and 'link' in key or key in {'title-link'}:
                targets.add(str(p.value).strip())
    out = JOB/'evidence/extra-links.json'
    if not out.exists():
        response = w.site('en').simple_request(action='query', prop='langlinks',
            titles='|'.join(sorted(targets)), lllang='mg', lllimit='max',
            redirects=1, formatversion=2).submit()
        write_json(out, {'retrieved_at': now(), 'response': response})
    out = JOB/'evidence/local-identity.json'
    if not out.exists():
        response = w.site('mg').simple_request(action='query', prop='extracts',
            titles="Tany|Marsa (planeta)|Volana|Meksika|Però|Tajikistàna|Silia|Repoblika Entim-Bahoakan' i Sina|Tiorkia|Testamenta Vaovao|Plinio Zokiny|Thales|Volkano|Magma|Napoli|Sicilia|Nosy Rhodos|Tendrombohitra|Valan-javaboarin'i Yellowstone",
            exintro=1, explaintext=1, exsentences=2, exlimit=20, formatversion=2).submit()
        write_json(out, {'retrieved_at': now(), 'response': response})
    out = JOB/'evidence/category-search.json'
    if not out.exists():
        response = w.site('mg').simple_request(action='query', list='search',
            srsearch='jeolojia OR jeôlôjia OR "loza voajanahary" OR horohorontany',
            srnamespace=14, srlimit=15, formatversion=2).submit()
        write_json(out, {'retrieved_at': now(), 'response': response})
    out = JOB/'evidence/category-membership.json'
    if not out.exists():
        response = w.site('mg').simple_request(action='query', prop='categories',
            titles='Loza voajanahary|Volkano|Tany', cllimit='max', formatversion=2).submit()
        write_json(out, {'retrieved_at': now(), 'response': response})
    print('Supplemental evidence pinned.')


if __name__ == '__main__':
    main()
