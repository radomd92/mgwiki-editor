"""Copy stable prior lookup pairs; does not contact a dictionary or Wikipedia."""
import shutil
from pathlib import Path
from mgwiki_editor.core import read_json, write_json

JOB=Path('runs/iliad-en-20261106')
SOURCES={
 'genji-en-20261105-utf8/evidence':['allusion','antihero','homophone','vernacular','extra-anthology','extra-opera','extra-loanword','extra-phonetic'],
 'oedipus-20261105/evidence':['fresco','lekythos','oracle','seer','trilogy','patronymic'],
 'alina-iraika-20261105':['automaton','critical-edition','couplet','prose','science-fiction','foreshadowing','thematic-patterning','recension'],
 'anne-brown-mos-20261103':['ballad','recital'],
 'baseball-20261106-r1/evidence':['extra-musical','extra-parody','extra-canon'],
}

def main():
 d=JOB/'evidence'/'reused'; d.mkdir(parents=True,exist_ok=True); index=[]
 for base,stems in SOURCES.items():
  for stem in stems:
   for edition in ('en','mg'):
    src=Path('runs')/base/('lookup-'+edition+'-'+stem+'.json')
    if not src.exists():continue
    dest=d/src.name
    if dest.exists():raise RuntimeError('Duplicate reuse destination')
    shutil.copyfile(src,dest)
    record=read_json(src)
    index.append(dict(original=str(src),copy=str(dest.relative_to(JOB)),edition=edition,word=record.get('word'),status=record.get('status'),retrieved_at=record.get('retrieved_at')))
 write_json(JOB/'reused-lookup-index.json',index)
 print('Copied',len(index),'prior dictionary responses; sense review still required')

if __name__=='__main__':main()
