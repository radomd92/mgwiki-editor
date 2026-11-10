"""Pin focused Wikipedia sections needed to resolve identified citation conflicts."""
from pathlib import Path
from mgwiki_editor.core import Wiki, write_json, read_json, now

JOB=Path('runs/iliad-en-20261106')

def main():
 wiki=Wiki();d=JOB/'evidence'
 for name,page in [('religion','Ancient Greek religion'),('military','Military of Mycenaean Greece'),('cassandra','Cassandra (novel)')]:
  p=d/(name+'-section-index.json')
  if not p.exists():
   data=wiki.site('en').simple_request(action='parse',page=page,prop='sections',formatversion=2).submit()
   write_json(p,dict(retrieved_at=now(),response=data))
  a=read_json(p)['response']['parse']
  print(name,'revision',a.get('revid'),[(s['index'],s['line']) for s in a['sections']])
 p=d/'audio-file.json'
 if not p.exists():write_json(p,dict(retrieved_at=now(),response=wiki.site('en').simple_request(action='query',prop='imageinfo',titles='File:en-us-Iliad.oga',iiprop='timestamp|extmetadata',formatversion=2).submit()))
 for name,page,sections in [('religion','Ancient Greek religion',['4','6','16']),('military','Military of Mycenaean Greece',['9','16']),('cassandra','Cassandra (novel)',['1'])]:
  for section in sections:
   p=d/(name+'-section-'+section+'.json')
   if not p.exists():
    data=wiki.site('en').simple_request(action='parse',page=page,section=section,prop='wikitext|revid',formatversion=2).submit()
    write_json(p,dict(retrieved_at=now(),response=data))
   a=read_json(p)['response']['parse'];s=a['wikitext']
   if isinstance(s,dict):s=s['*']
   (JOB/'conflict-pages'/(name+'-section-'+section+'.wiki')).write_text(s,encoding='utf-8')
   print(name,section,'revision',a.get('revid'))

if __name__=='__main__':main()
