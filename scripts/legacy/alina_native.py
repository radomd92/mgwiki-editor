"""Offline conversion of bibliographic templates, retaining source metadata."""
import re

import mwparserfromhell as mw


def native_citation(t):
    p={str(x.name).strip().lower():str(x.value).strip() for x in t.params}
    used=set()
    def take(k):
        used.add(k)
        return p.get(k,'')
    out=[]
    for prefix in ('author','editor','translator'):
        people=[]
        for n in ('',*[str(i) for i in range(1,8)]):
            full=take(prefix+n)
            last=take(('last' if prefix=='author' else prefix+'-last')+n)
            first=take(('first' if prefix=='author' else prefix+'-first')+n)
            # Numbered forms typically put the number before -last/-first.
            if n and prefix!='author':
                last=last or take(prefix+n+'-last')
                first=first or take(prefix+n+'-first')
            if n and prefix=='author':
                last=last or take('last'+n)
                first=first or take('first'+n)
            if full:
                people.append(full)
            elif prefix=='author' and last=='Ulrich Marzolph, Richard van Leeuwen' and first=='Hassan Wassouf':
                # The source bibliography explicitly lists these three authors.
                people.append('Ulrich Marzolph; Richard van Leeuwen; Hassan Wassouf')
            elif prefix=='author' and (last,first) in {
                ('Yuriko Yamanaka','Tetsuo Nishio'),
                ('Geraldine McCaughrean','Rosamund Fowler'),
            }:
                # Full names were placed in surname/given-name fields in source.
                people.append(last+'; '+first)
            elif first or last:
                people.append(' '.join(x for x in (first,last) if x))
        if people:
            out.append('; '.join(people)+({'author':'','editor':' (mpanonta)','translator':' (mpandika teny)'}[prefix]))
    title=take('title') or take('wstitle')
    url=take('url')
    if title:
        out.append("''"+(f'[{url} {title}]' if url else title)+"''")
    elif url:
        out.append(f'[{url} {url}]')
    for field,label in [('chapter',''),('encyclopedia',''),('journal',''),('work',''),('website',''),('series',''),('edition','fanontana '),('volume','boky '),('issue','laharana '),('location',''),('publisher',''),('date',''),('year',''),('orig-date','navoaka voalohany: '),('pages','p. '),('page','p. ')]:
        v=take(field)
        if v:
            if field in {'chapter','encyclopedia','journal','work','series'}:
                v="''"+v+"''"
            out.append(label+v)
    if str(t.name).strip().lower()=='cite eb1911':
        out.append("''Encyclopædia Britannica'', 1911, fanontana faha-11")
    for field,label in [('isbn','ISBN'),('issn','ISSN'),('doi','doi:'),('oclc','OCLC'),('jstor','JSTOR'),('s2cid','S2CID')]:
        v=take(field)
        if v:
            out.append('<nowiki>'+label+(' ' if not label.endswith(':') else '')+v+'</nowiki>')
    for field,label in [('language','fiteny: '),('access-date','nojerena tamin’ ny '),('archive-date','datin’ ny tahiry: '),('archive-url','rohy voatahiry: '),('url-status','toetry ny rohy: '),('quote','teny nalaina: '),('via','avy amin’ ny ')]:
        v=take(field)
        if v:
            if field=='archive-url':
                v=f'[{v} {v}]'
            out.append(label+v)
    for k,v in p.items():
        if k not in used and v:
            # Link targets are already represented by the displayed author name.
            if 'link' in k or k in {'postscript','ref','url-access','df'}:
                continue
            out.append(k+': '+v)
    return '. '.join(out).rstrip('.')+'.'


def convert(text):
    code=mw.parse(text)
    for t in reversed(code.filter_templates()):
        name=str(t.name).strip().lower().replace('_',' ')
        replacement=None
        if name.startswith('cite ') or name=='citation':
            replacement=native_citation(t)
        elif name in {'sfn','harvnb'}:
            pos=[str(x.value).strip() for x in t.params if str(x.name).strip().isdigit()]
            authors='; '.join(pos[:-1])
            year=pos[-1] if pos else ''
            titles={'Irwin':"''The Arabian Nights: A Companion''",'Pinault':"''Story-Telling Techniques in the Arabian Nights''",'Byatt':"''On Histories and Stories: Selected Essays''"}
            label=authors+', '+titles.get(authors,'')+', '+year
            for key in ('p','pp','loc'):
                if t.has(key):
                    label+=', '+('p. ' if key!='loc' else '')+str(t.get(key).value).strip()
            replacement='<ref>'+label+'.</ref>' if name=='sfn' else label
        elif name=='isbn':
            replacement='<nowiki>ISBN '+str(t.get(1).value).strip()+'</nowiki>'
        elif name=='doi':
            replacement='<nowiki>doi:'+str(t.get(1).value).strip()+'</nowiki>'
        elif name=='jstor':
            replacement='<nowiki>JSTOR '+str(t.get(1).value).strip()+'</nowiki>'
        elif name=='webarchive':
            p={str(x.name).strip():str(x.value).strip() for x in t.params}
            replacement='('+f"[{p['url']} Tahiry]"+(f", {p['date']}" if p.get('date') else '')+')'
        if replacement is not None:
            try:
                code.replace(t,replacement)
            except ValueError:
                pass
    return str(code)


if __name__=='__main__':
    import sys
    from pathlib import Path
    p=Path(sys.argv[1])
    p.write_text(convert(p.read_text(encoding='utf-8')),encoding='utf-8')
