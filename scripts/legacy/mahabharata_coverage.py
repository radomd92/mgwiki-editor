"""Offline content, citation, image and link accounting for the assembled draft."""
from pathlib import Path
from collections import Counter
import re
import mwparserfromhell as mw
from mgwiki_editor.core import read_json, write_json

JOB=Path('runs/mahabharata-20261108')


def urls(text):
    return set(re.findall(r'https?://[^\s<>\]|}]+',text))


if __name__=='__main__':
    source=(JOB/'source.wiki').read_text(encoding='utf-8')
    draft=(JOB/'draft.wiki').read_text(encoding='utf-8')
    src=mw.parse(source); code=mw.parse(draft)
    original_lines=source.splitlines()
    excluded='\n'.join(x for x in original_lines if 'Maharashtra builds up a case' in x or 'Indonesian Ramayana: The Uttarakanda' in x)
    # The Phalgunadi sentence shares a paragraph with retained Javanese/ANU claims:
    # exempt only the two exact abebooks reference URLs, never the whole paragraph.
    skipped_urls={u for u in urls(excluded) if 'livemint.com' in u or 'abebooks.com' in u}
    missing_urls=urls(source)-urls(draft)-skipped_urls
    files=lambda c:Counter(str(x.title).split(':',1)[1].strip().replace('_',' ') for x in c.filter_wikilinks()
                           if str(x.title).lower().startswith(('file:','image:')))
    expected=Counter(x.replace('_',' ') for x in read_json(JOB/'source-image-inventory.json'))
    image_diff=dict(missing=list((expected-files(code)).elements()),extra=list((files(code)-expected).elements()))
    refs=lambda c:[t for t in c.filter_tags() if str(t.tag).lower()=='ref']
    report=dict(source_references=len(refs(src)),draft_references=len(refs(code)),
                expected_reference_reduction=3,missing_source_urls=sorted(missing_urls),
                authorized_omitted_urls=sorted(skipped_urls),images=image_diff,
                source_images=sum(expected.values()),draft_images=sum(files(code).values()),
                categories=[str(l) for l in code.filter_wikilinks() if 'sokajy:' in str(l.title).lower()])
    mapping=read_json(JOB/'final-link-map.json'); links=[]
    for row in read_json(JOB/'section-plan.json'):
        ident=row['id']; text=(JOB/'sections'/ident/'source.wiki').read_text(encoding='utf-8')
        if ident=='25-family': text+='\n'+(JOB/'evidence/kuru-tree.wiki').read_text(encoding='utf-8')
        worker=(JOB/'sections'/ident/'section.wiki').read_text(encoding='utf-8')
        local=mw.parse(worker)
        labelmap={str(l.title).strip():str(l.text or l.title) for l in local.filter_wikilinks()}
        for l in mw.parse(text).filter_wikilinks():
            target=str(l.title).strip(); label=labelmap.get(target,str(l.text or l.title))
            if target.lower().startswith(('file:','image:')):
                disposition='Sary Commons voatahiry amin’ ity fizarana ity; caption sy alt nadika.'
            elif target.lower().startswith(('category:', 'sokajy:')):
                disposition='Sokajy source/template vahiny tsy afindra; Boky mg voamarina no fanampiny inert.'
            elif ident=='03-historical-references' and target not in labelmap:
                disposition='Filazana nesorina araka ny fahazoan-dalana avy amin’ ny mpampiasa, na plain-text fallback; jereo notes.wiki fizarana 03.'
            elif target.split('#')[0] in mapping and mapping[target.split('#')[0]].get('mg'):
                disposition='Target mg voamarina: '+mapping[target.split('#')[0]]['mg']
            else:
                disposition='Soratra tsotra ao amin’ ity fizarana ity; tsy voamarina ny target mg mitovy hevitra. Tsy mamorona rohy.'
            links.append(dict(section=ident,source_target=target,draft_label=label,disposition=disposition))
    write_json(JOB/'coverage-report.json',report)
    write_json(JOB/'source-to-draft-link-coverage.json',links)
    with (JOB/'notes.wiki').open('a',encoding='utf-8') as f:
        f.write('\n== Fanisana source mankany amin’ ny draft ==\n')
        f.write(f"Sary {sum(expected.values())}/{sum(files(code).values())}; references {len(refs(src))} → {len(refs(code))}. Ref :0 roa sy citation abebooks iray ihany no reduction; ny Garg dia naverina. Jereo coverage-report.json, source-to-draft-link-coverage.json, link-decisions.json ary worker-notes.wiki.\n")
        for x in links:
            f.write('* '+x['section']+': '+x['source_target']+' → '+x['draft_label']+'; '+x['disposition']+'\n')
        f.write('''Ny author-link sy title-link parameters ao amin' ny citation templates dia formatting targets fa tsy anarana bibliografika. Voatahiry ao amin' ny source sy template-conversion-inventory.json izy ireo; ny anarana/lohateny no voatahiry amin' ny citation native, ary tsy noforonina ho targets mg ireo targets en tsy voamarina. Tsy nafindra ny maintenance, navigation, authority-control, sister-project logos sy edit-Wikidata icons; tsy votoatin' ny tantara ireo ary tsy ilaina amin' ny bibliography native. Ny tracking categories sy dynamic access-date novokarin' ny expandtemplates dia tsy afindra: tsy filazana fa novakina ny tranonkala ivelany ny API expansion.
''')
    print(report)
