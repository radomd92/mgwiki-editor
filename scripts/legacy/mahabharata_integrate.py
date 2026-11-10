"""Merge section handoffs and retain explicit, reviewable coverage evidence."""
from pathlib import Path
import re
import shutil
import textwrap
import mwparserfromhell as mw
from genji_en_native import native_templates, map_links, param, italics
from mgwiki_editor.core import read_json, write_json, lint_wikitext, now

JOB=Path('runs/mahabharata-20261108')
HEADINGS={
 '01-textual-intro':"Tantaran' ny lahatsoratra sy ny firafiny",
 '02-redaction':'Fanitarana sy fanitsiana ny lahatsoratra',
 '03-historical-references':'Fanondroana ara-tantara',
 '04-books':'Ireo fizarana na boky 18', '05-history':'Toe-javatra ara-tantara',
 '06-synopsis-intro':'Famintinana ny tantara', '07-ancestors':'Ireo taranaka taloha',
 '08-princes':"Ireo zanak' andriana Pandava sy Kaurava", '09-lac-house':"Lakshagraha, ilay trano vita amin' ny ''lac''",
 '10-marriage':"Fanambadiana an' i Draupadi", '11-indraprastha':'Indraprastha',
 '12-dice':'Ilay lalao filokana', '13-exile':'Sesitany sy fiverenana',
 '14-battle':'Ny ady tao Kurukshetra', '15-end':"Ny fiafaran' ny Pandava",'16-reunion':'Fihaonana indray',
 '17-themes':'Lohahevitra','18-translations':'Dikan-teny, endrika samihafa ary sanganasa nipoitra avy aminy',
 '19-critical-edition':'Fanontana nampitahana sy nodinihina','20-literature':'Literatiora nipoitra avy aminy',
 '21-screen':'Sarimihetsika sy fahitalavitra','22-radio':'Fampifanarahana hafa',
 '23-folk':"Ao amin' ny kolontsain' ny vahoaka",'24-jain':'Dikan-teny jaina',
 '25-family':"Tetiaran' ny fianakaviana Kuru",'26-influence':'Fiantraikany ara-kolontsaina',
 '27-modern-translations':'Dikan-teny maoderina','28-notes':'Fanamarihana manazava',
 '29-citations':'Fanovozan-kevitra','30-sources':'Loharano ankapobeny','31-external':'Rohy ivelany',
}
MAJOR={'01-textual-intro','05-history','06-synopsis-intro','17-themes','18-translations',
       '25-family','26-influence','27-modern-translations','28-notes','29-citations','30-sources','31-external'}


def special_templates(text):
    expansions=read_json(JOB/'evidence/special-expansions.json')
    expanded=expansions['response']['expandtemplates']['wikitext']
    code=mw.parse(text)
    for t in list(code.filter_templates()):
        name=str(t.name).strip().lower()
        replacement=None
        if name=='cite banglapedia':
            replacement=('Mohanta, Sambaru Chandra (2012). [http://en.banglapedia.org/index.php?title=Mahabharata '
                         "''Mahabharata'']. Ao amin' ny Sirajul Islam; Miah, Sajahan; Khanam, Mahfuza; Ahmed, Sabbir (mpamoaka). "
                         "''Banglapedia: the National Encyclopedia of Bangladesh'' (fanontana an-tserasera). Dhaka, Bangladesh: "
                         'Banglapedia Trust, Asiatic Society of Bangladesh. <nowiki>ISBN 984-32-0576-6</nowiki>. '
                         '<nowiki>OCLC 52727562</nowiki>. <nowiki>OL 30677644M</nowiki>.')
        elif name=='imdb title':
            title=param(t,'title')
            qid=param(t,'qid')
            index={'Q3312543':1,'Q2917578':2}.get(qid)
            if index is None: raise ValueError('Unaccounted IMDb citation')
            block=expanded.split(f'EXTRACT {index}\n',1)[1].split(f'END EXTRACT {index}',1)[0]
            url=re.search(r'https://www.imdb.com/title/tt\d+/',block).group(0)
            replacement=f'[{url} {italics(title)}], IMDb (tahiry an-tserasera momba ny sarimihetsika).'
        elif name=='!': replacement='&#124;'
        elif name in {'page needed','citation needed'}: replacement=''
        if replacement is not None:
            try: code.replace(t,replacement)
            except ValueError: pass
    return native_templates(str(code))


def headings(ident,text):
    # Earlier Latin-1 readable numbering put a next heading at some fragment ends.
    # Remove only empty trailing headings, never substantive following content.
    text=re.sub(r'\n={2,6}[^\n]+={2,6}\s*\Z','\n',text.rstrip())
    if ident=='00-lead': return text
    code=mw.parse(text)
    hs=code.filter_headings()
    level=2 if ident in MAJOR else 3
    own='='*level+' '+HEADINGS[ident]+' '+'='*level
    # Keep internal subsection headings; replace an actual first own heading only.
    if hs and str(code).lstrip().startswith(str(hs[0])):
        h=hs[0]
        # Section18/27 may have subheadings but no leading main heading.
        if h.level==level: code.replace(h,own)
        else: return own+'\n'+str(code).strip()
        return str(code).strip()
    return own+'\n'+text.strip()


def integrate():
    plan=read_json(JOB/'section-plan.json')
    for row in plan:
        for name in ['section.wiki','notes.wiki','vocabulary.json']:
            if not (JOB/'sections'/row['id']/name).is_file():
                raise ValueError('Missing handoff: '+row['id']+'/'+name)
    mapping=read_json(JOB/'link-map.json')
    finalmap={k:dict(v) for k,v in mapping.items()}
    for k in ['god','God','vulgate','Vulgate']:
        if k in finalmap:
            finalmap[k]['rejected_target']=finalmap[k].get('mg')
            finalmap[k]['mg']=None
            finalmap[k]['reason']='Different material sense: monotheistic God/Bible Vulgate not Hindu gods/generic textual vulgate.'
    write_json(JOB/'final-link-map.json',finalmap)
    alltext=[]; vocab=[]; decisions=[]; templates=[]; allnotes=[]
    for row in plan:
        ident=row['id']; section=JOB/'sections'/ident
        raw=(section/'section.wiki').read_text(encoding='utf-8')
        templates.extend(dict(section=ident,original=str(t)) for t in mw.parse(raw).filter_templates())
        text=headings(ident,special_templates(raw))
        text,mapped=map_links(text,finalmap)
        decisions.extend(dict(section=ident,decision=x) for x in mapped)
        alltext.append(text)
        allnotes.append('== '+ident+' ==\n'+(section/'notes.wiki').read_text(encoding='utf-8'))
        for entry in read_json(section/'vocabulary.json'):
            if not isinstance(entry,dict): raise ValueError('Malformed vocabulary '+ident)
            files=[]
            for f in entry.get('evidence_files',[]):
                if (JOB/f).is_file(): files.append(f)
                elif (section/f).is_file(): files.append(str((section/f).relative_to(JOB)))
            entry['evidence_files']=sorted(set(files+['sections/'+ident+'/source.wiki','sections/'+ident+'/notes.wiki']))
            entry['worker_section']=ident
            vocab.append(entry)
        row['status']='integrated_pending_whole_article_review'
    # A relevant category was directly verified in earlier evidence; pin it locally.
    category_src=Path('runs/iliad-en-20261106-r1/evidence/categories.json')
    shutil.copyfile(category_src,JOB/'evidence/reused-book-category.json')
    text='\n\n'.join(alltext).rstrip()+"\n\n[[:Sokajy:Boky]]\n"
    (JOB/'draft.wiki').write_text(text,encoding='utf-8')
    (JOB/'draft-readable.txt').write_text('\n'.join('\n'.join(textwrap.wrap(l,170,break_long_words=False,break_on_hyphens=False,replace_whitespace=False,drop_whitespace=False)) for l in text.splitlines()),encoding='utf-8')
    (JOB/'worker-notes.wiki').write_text('\n\n'.join(allnotes),encoding='utf-8')
    write_json(JOB/'section-plan.json',plan)
    write_json(JOB/'merged-worker-vocabulary.json',vocab)
    write_json(JOB/'link-decisions.json',decisions)
    write_json(JOB/'template-conversion-inventory.json',templates)
    code=mw.parse(text)
    remaining=sorted({str(t.name) for t in code.filter_templates()})
    write_json(JOB/'integration-check.json',dict(updated_at=now(),sections=len(plan),
        remaining_templates=remaining,lint_errors=lint_wikitext(text),vocabulary_records=len(vocab),
        images=[str(l.title) for l in code.filter_wikilinks() if str(l.title).lower().startswith(('file:','image:'))],
        headings=[str(h) for h in code.filter_headings()]))
    print('Integrated',len(plan),'sections;',len(text),'characters; remaining templates',remaining)


if __name__=='__main__': integrate()
