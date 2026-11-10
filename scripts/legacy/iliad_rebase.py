"""One explicit safe rebase after a fully observed terminal-LF normalization."""
import shutil
from pathlib import Path
from mgwiki_editor.core import GATES, read_json, write_json, digest, now, lint_wikitext

OLD=Path('runs/iliad-en-20261106')
NEW=Path('runs/iliad-en-20261106-r1')

def main():
 old=read_json(OLD/'job.json');new=read_json(NEW/'job.json');inspection=read_json(OLD/'save-inspection.json')
 for key in ('source','existing'):
  for field in ('title','revision_id','sha256','text'):
   assert old[key][field]==new[key][field],(key,field)
 original=(OLD/'draft.wiki').read_bytes();observed=new['sandbox']['text'].encode('utf-8')
 assert original.endswith(b'\n') and original[:-1]==observed
 assert new['sandbox']['revision_id']==inspection['revision_id']==1153305
 assert inspection['text'].encode('utf-8')==observed
 assert (NEW/'draft.wiki').read_bytes()==observed
 assert not lint_wikitext(observed.decode('utf-8'))
 immutable={'job.json','source.wiki','existing.wiki','sandbox.wiki','draft.wiki','review.json'}
 for name in read_json(OLD/'proposal.json')['artifacts']:
  if name in immutable:continue
  target=NEW/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OLD/name,target)
 shutil.copytree(OLD/'sections',NEW/'sections',dirs_exist_ok=True)
 prior=NEW/'prior-attempt';prior.mkdir(exist_ok=True)
 for name in ('receipt.json','save-inspection.json','proposal.json','autonomous-preview-review.json'):
  shutil.copyfile(OLD/name,prior/name)
 plan=read_json(NEW/'section-plan.json')
 for r in plan:r['directory']=r['directory'].replace(str(OLD),str(NEW),1)
 write_json(NEW/'section-plan.json',plan)
 record={'recorded_at':now(),'status':'observed_exact_serialization_difference; original proposal not byte-confirmed','original_job':str(OLD),'rebased_job':str(NEW),'destination':new['destination'],'observed_revision':inspection['revision_id'],'original_proposal_sha256':digest(original),'observed_sha256':digest(observed),'difference':'one terminal LF removed by MediaWiki; all other UTF-8 bytes exactly equal','remote_retry_performed':False,'rebase_count':1}
 write_json(NEW/'serialization-reconciliation.json',record)
 with (NEW/'notes.wiki').open('a',encoding='utf-8') as f:f.write("""
== Rebase tokana taorian’ ny fanamarinana fandefasana ==
Ny publish voalohany dia nahazo edit response 200, saingy tsy nandalo ny exact read-back hash. Tsy naverina ilay publish. Novakiana indray indray mandeha tamin’ ny gateway ny destination, ary voaporofo fa revision 1153305 no misy: mitovy avokoa ny UTF-8 bytes rehetra afa-tsy LF iray any amin’ ny farany, izay tsy ao amin’ ny lahatsoratra voavaky. Voatahiry ho unconfirmed ny receipt/proposal voalohany; tsy noleferina ny exact-content guard ary tsy lazaina ho nahazo confirmation ilay digest voalohany.
Natao init vaovao indray mandeha ny runs/iliad-en-20261106-r1. Mitovy tanteraka amin’ ny pinned source sy mainspace taloha ireo snapshots vaovao, ary ny sandbox vaovao dia mitovy byte-for-byte amin’ ilay inspection voavaky. Izy io ihany no draft: tsy nisy prose, reference, sary, rohy na sokajy novana; tsy misy trailing LF amin’ ity proposal vaovao ity. Novakiana sy nampitahaina tamin’ ny source/sections efa nojerena feno ny votoaty mitovy; voatahiry byte-for-byte ny sandbox contribution vaovao, ka existing_preserved dia mihatra amin’ ny base vaovao fa tsy N/A intsony. Ny fanomanana/rendering sy review vaovao ary publish exact/no-change voaaro no atao, tsy blind retry. Tsy azo atao rebase fanindroany amin’ ity task ity. Ny porofo momba ilay ezaka voalohany dia ao amin’ ny prior-attempt/ sy serialization-reconciliation.json.
""")
 vocab=read_json(NEW/'vocabulary.json');vocab[-1]['evidence_files']=sorted(set(vocab[-1]['evidence_files']+['serialization-reconciliation.json']+['prior-attempt/'+n for n in ('receipt.json','save-inspection.json','proposal.json','autonomous-preview-review.json')]))
 write_json(NEW/'vocabulary.json',vocab)
 write_json(NEW/'review.json',dict.fromkeys(GATES,True))
 print('One rebase initialized; new draft exactly matches pinned live revision',inspection['revision_id'],'bytes',len(observed))

if __name__=='__main__':main()
