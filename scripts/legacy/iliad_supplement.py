"""Targeted source-conflict reads via Wiki, run only after first worker ends."""
from pathlib import Path
from mgwiki_editor.core import Wiki, read_json, write_json, now

JOB=Path('runs/iliad-en-20261106')

def main():
 wiki=Wiki(); p=JOB/'evidence'/'targeted-conflicts.json'
 if not p.exists():
  data=wiki.site('en').simple_request(action='query',prop='revisions',rvprop='ids|content',rvslots='main',titles='Glaucus (soldier)|Demetrios Chalkokondyles|Ilium (novel)|Jonathan Shay|Scamander|Shield of Achilles',formatversion=2).submit()
  write_json(p,dict(retrieved_at=now(),response=data))
 data=read_json(p)
 out=JOB/'conflict-pages';out.mkdir(exist_ok=True)
 for page in data['response']['query']['pages']:
  if page.get('revisions'):
   (out/(page['title'].replace('/','_')+'.wiki')).write_text(page['revisions'][0]['slots']['main']['content'],encoding='utf-8')
 print('Targeted snapshots pinned')

if __name__=='__main__':main()
