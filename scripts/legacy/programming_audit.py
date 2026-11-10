"""Offline coverage/integrity inventory; reports evidence, not editorial approval."""
import re
from collections import Counter
from pathlib import Path

import mwparserfromhell as mw

from mgwiki_editor.core import lint_wikitext, read_json, write_json
from programming_plan import JOB


def snippets(text):
    return [str(t.contents) for t in mw.parse(text).filter_tags()
            if str(t.tag).lower() in {'syntaxhighlight','source'}]


def urls(text):
    return Counter(re.findall(r'https?://[^\s|}\]<>"\']+',text))


def files(text):
    return [str(x.title).split(':',1)[1] for x in mw.parse(text).filter_wikilinks()
            if str(x.title).startswith(('File:','Sary:'))]


def main():
    source=(JOB/'source.wiki').read_text(encoding='utf-8')
    draft=(JOB/'draft.wiki').read_text(encoding='utf-8')
    report={'lint_errors':lint_wikitext(draft),
            'source_files':files(source),'draft_files':files(draft),
            'code_snippets_exact':snippets(source)==snippets(draft),
            'missing_urls':list((urls(source)-urls(draft)).elements()),
            'added_urls':list((urls(draft)-urls(source)).elements()),
            'sections':[]}
    for p in read_json(JOB/'section-plan.json'):
        d=Path(p['directory'])
        s=(d/'source.wiki').read_text(encoding='utf-8')
        t=(d/'section.wiki').read_text(encoding='utf-8')
        def citations(x):
            return Counter(str(c) for c in mw.parse(x).filter_templates()
                           if str(c.name).strip().lower().startswith('cite ')
                           or str(c.name).strip().lower() in {'sfn','isbn','webarchive'})
        report['sections'].append({'id':p['id'],
             'missing_citation_templates':list((citations(s)-citations(t)).elements()),
             'source_bytes':len(s.encode('utf-8')),'fragment_bytes':len(t.encode('utf-8')),
             'source_files':files(s),'fragment_files':files(t)})
    write_json(JOB/'coverage-audit.json',report)
    print(report)


if __name__=='__main__':
    main()
