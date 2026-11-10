"""Sequential guarded title/link/file/citation evidence, no external browsing."""
import re
from pathlib import Path
import mwparserfromhell as mw
from mgwiki_editor.core import Wiki, GuardError, lookup, now, read_json, write_json

JOB=Path('runs/iliad-en-20261106')

def main():
 d=JOB/'evidence'; d.mkdir(exist_ok=True)
 wiki=Wiki(); source=(JOB/'source.wiki').read_text(encoding='utf-8'); code=mw.parse(source)
 targets={str(x.title).split('#')[0].replace('_',' ').strip() for x in code.filter_wikilinks() if ':' not in str(x.title)}
 for t in code.filter_templates():
  if str(t.name).strip().lower() in {'main'}:
   targets.update(str(p.value).strip().split('{{')[0].strip() for p in t.params)
 targets=sorted(t for t in targets if t)
 files={str(x.title).split(':',1)[1] for x in code.filter_wikilinks() if str(x.title).lower().startswith(('file:','image:'))}
 files.add('Illiad fragmented papyrus.png')
 requests=[('title-evidence.json','mg',dict(prop='revisions',rvprop='ids|content',rvslots='main',titles='Iliasy|Iliady|Iliade|Iliad|Boky|Mpikambana:Bot-Jagwar/Iliady|Mpikambana:Bot-Jagwar/Iliade|Mpikambana:Bot-Jagwar/Iliad')),
 ('categories.json','mg',dict(prop='info',titles='Sokajy:Boky|Sokajy:Literatiora|Sokajy:Literatiora grika|Sokajy:Tononkalo|Sokajy:Angano grika')),
 ('files.json','en',dict(prop='imageinfo',titles='|'.join('File:'+f for f in sorted(files)),iiprop='timestamp|extmetadata'))]
 for name,lang,params in requests:
  p=d/name
  if not p.exists(): write_json(p,dict(retrieved_at=now(),response=wiki.site(lang).simple_request(action='query',formatversion=2,**params).submit()))
 for start in range(0,len(targets),45):
  p=d/f'links-{start:03}.json'
  if not p.exists():
   response=wiki.site('en').simple_request(action='query',prop='langlinks',titles='|'.join(targets[start:start+45]),lllang='mg',lllimit='max',formatversion=2).submit()
   write_json(p,dict(retrieved_at=now(),response=response))
   if 'continue' in response: raise GuardError('Link metadata continuation needs targeted handling')
 mapping={}
 for p in sorted(d.glob('links-*.json')):
  data=read_json(p)['response']
  for page in data['query']['pages']:
   mapping[page['title']]={'mg':page.get('langlinks',[{}])[0].get('title'),'missing':page.get('missing',False),'evidence_file':str(p.relative_to(JOB))}
  for n in data['query'].get('normalized',[]):
   if n['to'] in mapping: mapping[n['from']]=mapping[n['to']]
 write_json(JOB/'link-map.json',mapping)
 mg=sorted({v['mg'] for v in mapping.values() if v.get('mg')})
 for start in range(0,len(mg),45):
  p=d/f'mg-verify-{start:03}.json'
  if not p.exists(): write_json(p,dict(retrieved_at=now(),response=wiki.site('mg').simple_request(action='query',prop='info',titles='|'.join(mg[start:start+45]),formatversion=2).submit()))
 templates={str(t) for t in code.filter_templates() if str(t.name).strip().lower() in {'oetymd','lsj','iliad','herodotus','standardebooks','librivox book','library resources box'}}
 p=d/'template-expansions.json'
 if not p.exists():
  # Single paced API expansion, not following any generated link.
  text='\n\n'.join('EXTRACT '+str(i)+'\n'+t+'\nEND EXTRACT '+str(i) for i,t in enumerate(sorted(templates)))
  result=wiki.site('en').simple_request(action='expandtemplates',title='Iliad',text=text,prop='wikitext',formatversion=2).submit()
  write_json(p,dict(retrieved_at=now(),inputs=sorted(templates),response=result))
 terms=[('epic','tononkalo'),('dactyl','tononkalo'),('hexameter','andininy'),('philology','filôlôjia'),('epithet','anarana'),('rhapsode','mpitantara'),('concubine','vadikely'),('plague','valanaretina'),('kleos','voninahitra'),('hubris','avonavona'),('manuscript','sora-tanana'),('scholium','fanamarihana'),('phalanx','tafika'),('palimpsest','sora-tanana'),('homophonic translation','fanononana'),('post-traumatic stress disorder','ratram-po'),('moral injury','fahatsiarovan-tena')]
 for en,mgword in terms:
  for edition,word in [('en',en),('mg',mgword)]:
   p=d/('lookup-'+edition+'-'+re.sub(r'[^a-z0-9]+','-',en)+'.json')
   if p.exists(): continue
   try: result=lookup(edition,word)
   except GuardError as e: result=dict(status='failed',edition=edition,word=word,retrieved_at=now(),error=str(e))
   write_json(p,result)
 print('Pinned',len(targets),'link targets,',len(files),'files,',len(terms),'sense pairs')

if __name__=='__main__': main()
