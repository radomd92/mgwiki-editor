"""One guarded rebase after inspecting exact server-side final-LF removal."""
from pathlib import Path
import shutil
from mgwiki_editor.core import Wiki, initialize, read_json, write_json, GuardError

OLD=Path('runs/mahabharata-20261108')
NEW=Path('runs/mahabharata-20261108-r1')


if __name__=='__main__':
    live=read_json(OLD/'save-inspection.json')
    expected=(OLD/'draft.wiki').read_bytes().decode('utf-8')
    receipt=read_json(OLD/'receipt.json')
    if not expected.endswith('\n') or live['text']!=expected[:-1]:
        raise GuardError('Inspection is not exactly one final LF removed; stop without another write.')
    if receipt['status']!='unconfirmed' or receipt['destination']!=live['title']:
        raise GuardError('Unexpected original receipt/destination.')
    fresh=initialize(Wiki(),NEW,'en','Mahabharata','Mahabharata',existing_title='Mahabharata')
    old=read_json(OLD/'job.json')
    for key in ['source','existing']:
        if fresh[key]['sha256']!=old[key]['sha256'] or fresh[key]['revision_id']!=old[key]['revision_id']:
            raise GuardError('Source/existing changed during the single rebase.')
    if fresh['sandbox']['revision_id']!=live['revision_id'] or fresh['sandbox']['sha256']!=live['sha256']:
        raise GuardError('Destination changed after one save inspection.')
    skip={'job.json','draft.wiki','source.wiki','existing.wiki','sandbox.wiki','proposal.json',
          'preview.html','changes.diff','receipt.json','status.json','proposal-review.wiki',
          'draft-readable.txt','offline-preview-audit.json','offline-preview-text.txt','offline-preview-tables.txt'}
    for p in OLD.iterdir():
        if p.name in skip: continue
        dest=NEW/p.name
        if p.is_dir(): shutil.copytree(p,dest,dirs_exist_ok=True)
        else: shutil.copyfile(p,dest)
    if (NEW/'draft.wiki').read_bytes()!=live['text'].encode('utf-8'):
        raise GuardError('New initial draft differs from exact inspected sandbox bytes.')
    shutil.copyfile(OLD/'receipt.json',NEW/'evidence/prior-unconfirmed-receipt.json')
    vocab=read_json(NEW/'vocabulary.json')
    for e in vocab:
        if e['source_term']=='Mahabharata' and e['domain']=='topic identity and edition provenance':
            e['evidence_files']=sorted(set(e['evidence_files']+['save-inspection.json','save-inspection.diff','evidence/prior-unconfirmed-receipt.json']))
    write_json(NEW/'vocabulary.json',vocab)
    with (NEW/'notes.wiki').open('a',encoding='utf-8') as out:
        out.write('''
== Rebase tokana taorian' ny fanamarinana ny save ==
Nandefa edit ny job voalohany. Ny CLI read-back sy ny inspection tokana manaraka dia nahita revision 1153350, hash 3be8fee5816cc8a13acbf9f94f59d9d3407bc0214d83dbf29cba4d2b89a9ad07. Ny LF iray farany ihany no nesorin' ny server; tsy nisy byte hafa niova. Tsy novaina ho confirmed an-jambany ny receipt voalohany ary tsy naverina ilay write tsy fantatra vokatra. Ny inspection dia nametra mazava ny exact text sy revision voatahiry.
Natao init vaovao iray ihany, izay nanamarina fa tsy niova ny source sy existing ary mitovy amin' ny inspection ny sandbox. Ilay exact sandbox text tsy misy LF farany no draft vaovao, byte-for-byte. Tsy namorona fandikana na nanaisotra user work: ilay lahatsoratra vao avy nalefan' ity asa ity manontolo no notazonina. Ny source sy existing hash dia mitovy tanteraka amin' ireo snapshots efa novakina; ny fanamarinana editorial dia mbola mihatra satria tsy nisy prose, isa, citation, sary na rohy niova. Ny merge/existing-preserved dia voamarina indray amin' ny sandbox vaovao izay mitovy amin' ny draft.
Mila prepare sy offline review vaovao mifamatotra amin' ny digest vaovao ny proposal. Ny publish manaraka dia manamarina exact bytes sy baserevid vaovao; tsy misy fampahalemena ny exact-hash guards, tsy misy force na automatic blind retry. Raha tsy miova ny sandbox dia tsy misy fanitsiana votoaty vaovao ilaina. Tsy azo atao rebase faharoa amin' ity task ity raha misy olana hafa.
''')
    write_json(NEW/'status.json',dict(status='single_rebase_after_inspected_final_lf_normalization',
        prior_job=str(OLD),rebase_count=1,inspected_revision=live['revision_id'],
        exact_inspected_sha256=live['sha256'],prepared=False,published=False))
    print('Single guarded rebase prepared locally:',NEW,'exact sandbox revision',live['revision_id'])
