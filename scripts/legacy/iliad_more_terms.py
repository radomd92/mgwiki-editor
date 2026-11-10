"""Additional paced sense checks and explicit Glaucus redirect resolution."""
import re
from pathlib import Path
from mgwiki_editor.core import Wiki, lookup, now, write_json, read_json, GuardError

JOB=Path('runs/iliad-en-20261106')
PAIRS=[('timē','haja'),('nostos','fiverenana'),('menis','hatezerana'),('oral-formulaic','raikipitenenana'),('simile','fanoharana'),('anthropomorphism',"endrik'olombelona"),('consciousness','fahatsiarovan-tena'),('bicameral mind','saina'),('ellipsis','fanafohezana'),('genitive','zenitiva'),('gloss','fanazavana'),('textual criticism','fandinihana'),('iamb','iamba'),('pentameter','andalana'),('blank verse','tononkalo'),('fourteener','andininy'),('heroic couplet','andalana'),('hoplite','miaramila'),('rhyme','rima'),('syntactic','fitsipi-pitenenana')]

def main():
 d=JOB/'evidence';wiki=Wiki();p=d/'glaucus-resolved.json'
 if not p.exists():
  response=wiki.site('en').simple_request(action='query',prop='revisions',rvprop='ids|content',rvslots='main',titles='Glaucus (son of Hippolochus)',formatversion=2).submit()
  write_json(p,dict(retrieved_at=now(),response=response))
  for page in response['query']['pages']:
   if page.get('revisions'):(JOB/'conflict-pages'/'Glaucus (son of Hippolochus).wiki').write_text(page['revisions'][0]['slots']['main']['content'],encoding='utf-8')
 for en,mg in PAIRS:
  for edition,word in [('en',en),('mg',mg)]:
   p=d/('lookup-'+edition+'-extra-'+re.sub('[^a-z0-9]+','-',en.lower())+'.json')
   if p.exists():continue
   try:result=lookup(edition,word)
   except GuardError as e:
    result=dict(status='failed',edition=edition,word=word,retrieved_at=now(),error=str(e))
    write_json(p,result)
    if any(x in str(e).lower() for x in ('cooldown','overload','deferred','429','503')):raise
   write_json(p,result)
 print('Additional sense pairs pinned:',len(PAIRS))

if __name__=='__main__':main()
