"""Offline loss-accounted native template adaptation for Iliad fragments."""
import re
from copy import deepcopy
import mwparserfromhell as mw
from mgwiki_editor.core import GuardError
from genji_en_native import citation, italics, param

MAINTENANCE={'page needed','citation needed','full citation needed','better source needed','failed verification','original research section','unreferenced section','dead link','cbignore','div col','div col end','portal','authority control','iliad navbox','epic cycle','homer','theban kings','national epic poems'}

def native(text,expansions=None):
 expansions=expansions or {}
 code=mw.parse(text)
 for t in reversed(list(code.filter_templates())):
  n=str(t.name).strip().lower(); r=None
  if n.startswith('cite '):
   # Preserve parameter boundaries after child {{!}} becomes a literal pipe.
   # Re-parsing str(t) here would incorrectly split protected citation titles.
   clean=deepcopy(t)
   for field in clean.params:
    for comment in list(field.value.filter_comments()):
     try:field.value.replace(comment,'')
     except ValueError:pass
   aliases={'author-last':'last','author-first':'first'}
   for i in range(1,10):
    suffix='' if i==1 else str(i)
    aliases.update({f'editor{i}-last':'editor-last'+suffix,f'editor{i}-first':'editor-first'+suffix,f'editor-last{i}':'editor-last'+suffix,f'editor-first{i}':'editor-first'+suffix})
   for old,new in aliases.items():
    if clean.has(old) and not clean.has(new):
     value=deepcopy(clean.get(old).value);clean.remove(old);clean.add(new,value)
   for key in ('ref','title-link','translator-link','translator1-link','translator2-link'):
    if clean.has(key):clean.remove(key)
   r=citation(clean)
  elif n in {'sfnp','sfn','sfnb','harvp','harvnp','harv'}:
   vals=[param(t,str(i)) for i in range(1,6) if param(t,str(i))]
   year=vals[-1] if vals else ''; authors=vals[:-1]
   s='; '.join(authors)+' ('+year+')'
   if p:=param(t,'p'):s+=', p. '+p
   if p:=param(t,'pp'):s+=', pp. '+p
   if p:=param(t,'loc'):s+=', '+p
   r=s if n.startswith('harv') else '<ref>'+s+'.</ref>'
  elif n=='harvc':
   authors=[]
   for suffix in ('','1','2','3'):
    if param(t,'last'+suffix) or param(t,'first'+suffix): authors.append(', '.join(x for x in (param(t,'last'+suffix),param(t,'first'+suffix)) if x))
   s='; '.join(authors)+' ('+param(t,'year')+'). '+italics(param(t,'chapter'))
   container=param(t,'in')
   containers={'R. Fowler':"Robert Fowler (mpamoaka), ''The Cambridge Companion to Homer''",'Pache':"Corinne Ondine Pache (mpamoaka), ''The Cambridge Guide to Homer''"}
   if container:s+='; '+containers.get(container,container)
   if p:=param(t,'pages'):s+=', pp. '+p
   r=s+'.'
  elif n in {'harvid','sfnref'}:r=''
  elif n in {'transliteration','transl'}:r=italics(param(t,'2'))
  elif n=='lang':r=param(t,'2')
  elif n in {'langx','lang-x'}:
   r=param(t,'2') or param(t,'text')
   if p:=param(t,'translit'):r+=' ('+italics(p)+')'
   if p:=param(t,'lit'):r+=' ('+p+')'
  elif n=='isbn':r='<nowiki>ISBN '+param(t,'1')+'</nowiki>'
  elif n=='jstor':r='<nowiki>JSTOR '+param(t,'1')+'</nowiki>'
  elif n=='!':r='|'
  elif n=='nbsp':r='&#160;'
  elif n=="'":r="&#39;"
  elif n in {'circa','c.'}:r='tokony ho '+param(t,'1')
  elif n=='rp':r=' (p. '+param(t,'1')+')'
  elif n=='efn':r='<ref group="fanamarihana">'+param(t,'1')+'</ref>'
  elif n=='notelist':r='<references group="fanamarihana" />'
  elif n=='reflist':r='<references />'
  elif n=='webarchive':
   r='['+param(t,'url')+' tahiry'+(' tamin’ ny '+param(t,'date') if param(t,'date') else '')+']'
  elif n=='multiref':r=' '.join(str(p.value).strip() for p in t.params)
  elif n=='main':r='Jereo koa: '+', '.join('[['+str(p.value).strip()+']]' for p in t.params)+'.'
  elif n=='interlanguage link':r=param(t,'1')
  elif n=='commons category':r='[https://commons.wikimedia.org/wiki/Category:'+param(t,'1').replace(' ','_')+' Sary sy tahiry momba ny '+param(t,'1')+' ao amin’ ny Wikimedia Commons]'
  elif n=='wikisource':
   if param(t,'1')=='el':r='[https://el.wikisource.org/wiki/'+param(t,'2')+' '+italics(param(t,'3') or param(t,'2'))+' amin’ ny teny grika ao amin’ ny Wikisource]'
   else:r='[https://en.wikisource.org/wiki/'+param(t,'1').replace(' ','_')+' '+italics(param(t,'2') or param(t,'1'))+' ao amin’ ny Wikisource anglisy]'
  elif n=='standardebooks':r='['+param(t,'Standard Ebooks URL')+' '+(param(t,'Display Name') or "''The Iliad''")+']'
  elif n=='library resources box':r='\n* [https://ftl.toolforge.org/cgi-bin/ftl?st=wp&su=Iliad&library=OLBP Boky azo vakina an-tserasera]\n* [https://ftl.toolforge.org/cgi-bin/ftl?st=wp&su=Iliad Tahiry ao amin’ ny tranomboky]\n* [https://ftl.toolforge.org/cgi-bin/ftl?st=wp&su=Iliad&library=0CHOOSE0 Tahiry ao amin’ ny tranomboky hafa]\n'
  elif n in MAINTENANCE:r=''
  elif n in {'poemquote','poem quote'}:
   r='<blockquote>'+param(t,'text')+'</blockquote>\n'+param(t,'source')
  elif n in {'iliad','herodotus'}:
   vals=[param(t,str(i)) for i in range(1,6) if param(t,str(i))]
   vals=[v for v in vals if v not in {'en','shortref','ref'}]
   work="Homer, ''Iliad''" if n=='iliad' else "Herodotus, ''Histories''"
   locator='.'.join(vals[:2])+('–'+vals[2] if len(vals)>2 else '')
   r=work+' '+locator
   # Source Iliad/Herodotus templates with ref positional argument are locators,
   # not permission to invent an external retrieval or a new bibliographic source.
  elif str(t) in expansions:r=expansions[str(t)]
  if r is None:raise GuardError('Unadapted template: '+str(t))
  try:code.replace(t,r)
  except ValueError:pass
 return str(code)

def dedupe_references(text):
 code=mw.parse(text); definitions={}
 for tag in list(code.filter_tags()):
  if str(tag.tag).strip().lower()!='ref' or tag.self_closing or not tag.has('name'):continue
  name=str(tag.get('name').value).strip('\"\' ')
  group=str(tag.get('group').value).strip('\"\' ') if tag.has('group') else ''
  key=(group,name); contents=str(tag.contents).strip()
  if key in definitions:
   if definitions[key]!=contents:raise GuardError('Conflicting reference '+repr(key))
   replacement='<ref name="'+name+'"'+(' group="'+group+'"' if group else '')+' />'
   code.replace(tag,replacement)
  else:definitions[key]=contents
 return str(code)
