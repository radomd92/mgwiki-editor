"""Use existing assembler/formatter; adapt unsupported reference wrappers offline."""
import json
import sys
from pathlib import Path
import mwparserfromhell as mw
from mgwiki_editor.workflow import assemble_sections
from mgwiki_editor.wikitext import literal_citation

p=Path('runs/gupta-empire-20261122').resolve()
assembly = sys.argv[1] if len(sys.argv) > 1 else 'assembly-v2'
assemble_sections(p,output=p/assembly)
code=mw.parse((p/assembly/'draft.wiki').read_text(encoding='utf-8'))
changes=[]
for t in reversed(code.filter_templates()):
    name=str(t.name).strip().replace('_',' ').casefold()
    original=str(t)
    value=lambda key: str(t.get(key).value).strip() if t.has(key) else ''
    replacement=None
    if name=='citation' or name.startswith('cite '):
        replacement=literal_citation(t)
        title=value('title')
        if title: replacement=replacement.replace('title: '+title, "title: ''"+title+"''",1)
        chapter=value('chapter')
        if chapter: replacement=replacement.replace('chapter: '+chapter, "chapter: ''"+chapter+"''",1)
        for param in t.params:
            key=str(param.name).strip();v=str(param.value).strip()
            if v.startswith(('https://','http://')) and not any(c in v for c in ' []\n'):
                replacement=replacement.replace(key+': '+v,key+': ['+v+']',1)
            if key.casefold() == 'isbn' and v:
                replacement=replacement.replace(key+': '+v,'<nowiki>'+key+': '+v+'</nowiki>',1)
    elif name in ('sfn','harvnb'):
        pos=[value(str(i)) for i in range(1,8) if value(str(i))]
        year=pos[-1];authors=', '.join(pos[:-1])
        body=authors+' ('+year+')'
        for param in t.params:
            key=str(param.name).strip();v=str(param.value).strip()
            if key.isdigit() or not v:continue
            if key in ('p','pp'):body+=', '+key+'. '+v
            elif key=='ps':body+=v
            else:body+='; '+key+': '+v
        replacement='<ref>'+body+'</ref>' if name=='sfn' else body
    elif name=='efn':
        content=mw.parse(value('1'))
        for tag in list(content.filter_tags()):
            if str(tag.tag).strip()=='ref' and tag.contents is not None:
                content.replace(tag,' ('+str(tag.contents)+')')
        replacement='<ref group="note">'+str(content)+'</ref>'
    elif name=='webarchive':replacement='['+value('url')+' Tahiry, '+value('date')+']'
    elif name=='rp':replacement=' (p. '+value('1')+')'
    elif name=='british-museum-db':replacement='[https://www.britishmuseum.org/collection/object/'+value('2')+' '+value('1')+']'
    elif name=='!':replacement='&#124;'
    elif name in ('refbegin','refend','citation needed'):replacement=''
    if replacement is not None:
        code.replace(t,replacement)
        changes.append({'source':original,'replacement':replacement})
text=str(code)
# Known free-text bibliographic titles; wording and surrounding evidence retained.
for title in ['The Huns','The First Spring: The Golden Age of India','Indian Esoteric Buddhism: Social History of the Tantric Movement']:
    text=text.replace('>'+title+' by ',">''"+title+"'' by ")
text=text.replace('>The Huns, Hyun Jin Kim',">''The Huns'', Hyun Jin Kim")
text+='\n* [https://en.wikisource.org/wiki/1911_Encyclop%C3%A6dia_Britannica/Gupta Lahatsoratra « Gupta » ao amin\' ny \'\'Encyclopædia Britannica\'\', fanontana 1911]\n* [https://commons.wikimedia.org/wiki/Category:Gupta_Empire Sary sy rakitra momba ny Empira Gupta ao amin\' ny \'\'Wikimedia Commons\'\' (tahirin-drakitra iombonan\' ny tetikasa Wikimedia)]\n\n[[Sokajy:India]]\n'
(p/'draft.wiki').write_text(text,encoding='utf-8')
(p/('native-adaptations-'+assembly+'.json')).write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
print('Native draft written',len(text.encode('utf-8')),'bytes',len(changes),'template adaptations')
