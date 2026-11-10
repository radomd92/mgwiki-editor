"""Coordinator-only offline assembly of accepted Iliad section fragments."""
import re
from pathlib import Path
import mwparserfromhell as mw
from mgwiki_editor.core import read_json, write_json, lint_wikitext, GuardError
from iliad_native import native, dedupe_references

JOB=Path('runs/iliad-en-20261106')

def harmonize(text):
 code=mw.parse(text)
 words={'Achaeans':'Achaean','Akeana':'Achaean','Akeanina':'Achaean','Akhaiana':'Achaean','akeana':'acha ean','akhaiana':'acha ean','akeanina':'acha ean','Trojanina':'Troiana','trojanina':'troiana','Troie':'Troy','Trôia':'Troy'}
 def walk(c):
  for node in list(c.nodes):
   if isinstance(node,mw.nodes.Text):
    s=str(node)
    for a,b in words.items():s=re.sub(r'(?<!\w)'+re.escape(a)+r'(?!\w)',b,s)
    s=s.replace('acha ean','Achaean')
    c.replace(node,s)
   elif isinstance(node,mw.nodes.Wikilink):
    if node.text is not None:walk(node.text)
   elif isinstance(node,mw.nodes.Heading):walk(node.title)
   elif isinstance(node,mw.nodes.Tag):
    if str(node.tag).lower() not in {'ref','nowiki','i','b'} and node.contents is not None:walk(node.contents)
 walk(code)
 return str(code)

def expansions():
 data=read_json(JOB/'evidence/template-expansions.json');text=data['response']['expandtemplates']['wikitext'];out={}
 for i,original in enumerate(data['inputs']):
  result=re.search('EXTRACT '+str(i)+r'\n(.*?)\nEND EXTRACT '+str(i),text,re.S).group(1)
  n=str(mw.parse(original).filter_templates()[0].name).strip().lower()
  if n=='oetymd':out[original]="Harper, Douglas. [https://www.etymonline.com/word/iliad ''iliad'']. ''Online Etymology Dictionary''."
  elif n=='lsj':
   code=mw.parse(result)
   for link in list(code.filter_wikilinks()):
    if str(link.title).startswith('Category:'):code.replace(link,'')
   out[original]='\n'+str(code)+'\n'
  elif n=='librivox book':
   url=str(mw.parse(result).filter_external_links()[0].url)
   out[original]='['+url+" ''The Iliad'', boky rakipeo azon’ ny besinimaro ampiasaina ao amin’ ny LibriVox]"
 return out

def restore_history(text,mapping):
 # Worker recorded English targets inert, keeping verified local links. Restore
 # selected same-topic links not already present, without guessing destinations.
 labels={
 'Homer':'Homer','Greece':'Grisia','Classical antiquity':'Andro Taloha klasika','Byzantine Empire':'tontolo bizantina','Florence':'Florence',
 }
 code=mw.parse(text)
 for en,label in labels.items():
  mg=mapping.get(en,{}).get('mg')
  if not mg:continue
  if any(str(l.title)==mg or str(l.title)==en for l in code.filter_wikilinks()):continue
  done=False
  for node in code.nodes:
   if isinstance(node,mw.nodes.Text) and label in str(node):
    code.replace(node,str(node).replace(label,'[['+mg+'|'+label+']]',1));done=True;break
  if done:continue
 return str(code)

def map_links(text,mapping):
 code=mw.parse(text);decisions=[];verified={v['mg'] for v in mapping.values() if v.get('mg')}
 for link in list(code.filter_wikilinks()):
  target=str(link.title).strip();label=str(link.text) if link.text is not None else target
  if re.match(r'(?i)^:?(?:File|Image|Sary):',target) or target.startswith(('#',':Sokajy:')):continue
  if target in verified:continue
  base,_,anchor=target.partition('#');mg=mapping.get(base.replace('_',' '),{}).get('mg')
  if target=='United States' and label in {'Amerika','America','Etazonia'}:label='Etazonia'
  if mg:
   replacement='[['+mg+('|' +label if label!=mg else '')+']]'
   decision=target+' → '+mg+(' (vatofantsika anglisy nesorina)' if anchor else '')
  else:replacement=label;decision=target+' → soratra tsotra: tsy misy pejy malagasy mitovy lohahevitra voamarina'
  try:code.replace(link,replacement);decisions.append(decision)
  except ValueError:pass
 return str(code),decisions

def main():
 plan=read_json(JOB/'section-plan.json');mapping=read_json(JOB/'link-map.json');ex=expansions();fragments=[];notes=[];vocab=[];all_decisions=[]
 for r in plan:
  d=JOB/'sections'/r['id']
  for filename in ('section.wiki','notes.wiki','vocabulary.json'):
   if not (d/filename).is_file():raise GuardError('Missing '+str(d/filename))
  text=(d/'section.wiki').read_text(encoding='utf-8')
  if not text.strip():raise GuardError('Empty section '+r['id'])
  if r['id']=='11-history':text=restore_history(text,mapping)
  text=harmonize(text)
  text=native(text,ex)
  text,decisions=map_links(text,mapping)
  fragments.append(text.strip());all_decisions.extend((r['id']+': '+x for x in decisions))
  notes.append('== '+r['id']+' ==\n'+(d/'notes.wiki').read_text(encoding='utf-8'))
  for v in read_json(d/'vocabulary.json'):
   v=dict(v);v['section_id']=r['id'];evidence=[]
   for p in v.get('evidence_files',[]):
    if (JOB/p).is_file():evidence.append(p)
    elif (d/p).is_file():evidence.append(str((d/p).relative_to(JOB)))
    else:raise GuardError('Invalid evidence '+p+' in '+r['id'])
   v['evidence_files']=evidence or [str((d/'source.wiki').relative_to(JOB))]
   vocab.append(v)
  r['status']='integrated_pending_coordinator_review'
 draft=dedupe_references('\n\n'.join(fragments)+'\n')
 draft+='\n[[:Sokajy:Boky]]\n[[:Sokajy:Angano grika]]\n'
 (JOB/'draft.wiki').write_text(draft,encoding='utf-8')
 (JOB/'section-handoff-notes.wiki').write_text('\n\n'.join(notes),encoding='utf-8')
 (JOB/'link-decisions.wiki').write_text('= Rohy tao amin’ ny fragments =\n'+'\n'.join('* '+x for x in all_decisions)+'\n',encoding='utf-8')
 write_json(JOB/'vocabulary.json',vocab);write_json(JOB/'section-plan.json',plan)
 print('Assembled',len(plan),'sections;',len(vocab),'memo entries;',len(draft.encode()),'bytes')
 print('Lint:',lint_wikitext(draft))

if __name__=='__main__':main()
