"""One guarded rebase after an inspected server-side final-newline normalization."""
import shutil
from pathlib import Path

from mgwiki_editor.core import GuardError, Wiki, initialize, read_json, write_json

OLD=Path('runs/baseball-20261106')
NEW=Path('runs/baseball-20261106-r1')


def main():
    inspected=read_json(OLD/'save-inspection.json')
    expected=(OLD/'draft.wiki').read_text(encoding='utf-8')
    if not expected.endswith('\n') or inspected['text']!=expected[:-1]:
        raise GuardError('Inspection does not establish only final-newline removal; stop.')
    state=initialize(Wiki(),NEW,'en','Baseball','Baseball',existing_title='Baseball')
    previous=read_json(OLD/'job.json')
    for name in ['source','existing']:
        if state[name]['sha256']!=previous[name]['sha256']:
            raise GuardError('Source/existing changed during the single rebase; stop.')
    if state['sandbox']['revision_id']!=inspected['revision_id'] or state['sandbox']['sha256']!=inspected['sha256']:
        raise GuardError('Destination changed after save inspection; stop.')
    skip={'job.json','draft.wiki','source.wiki','existing.wiki','sandbox.wiki',
          'proposal.json','preview.html','changes.diff','receipt.json','status.json',
          'preview-review.wiki','preview-readable.txt','draft-readable.txt'}
    for path in OLD.iterdir():
        if path.name in skip:
            continue
        target=NEW/path.name
        if path.is_dir():shutil.copytree(path,target,dirs_exist_ok=True)
        else:shutil.copyfile(path,target)
    # init's initial draft is the exact inspected on-wiki text, including no final LF.
    if (NEW/'draft.wiki').read_bytes()!=inspected['text'].encode('utf-8'):
        raise GuardError('New draft is not exact inspected bytes.')
    with (NEW/'notes.wiki').open('a',encoding='utf-8') as f:
        f.write('\n== Famerenana tokana taorian’ ny fanamarinana ny save ==\n')
        f.write('* Nandefa edit ny asa voalohany, ary ny read-back dia nahita revision '+str(inspected['revision_id'])+'. Tsy nifanandrify ny hash satria nesorin’ ny server ny LF iray farany; tsy nisy byte hafa niova. Tsy novaina ho confirmed an-jambany ny receipt voalohany ary tsy naverina ilay write.\n')
        f.write('* save-inspection.json sy save-inspection.diff dia voavaky; ny bytes marina voatahiry sy ny revision dia fantatra. Init vaovao iray ihany no natao, ka nitovy hatrany ny source/existing sy ny sandbox voamarina.\n')
        f.write('* Ny sandbox efa misy dia ilay dika voamarina avy amin’ ity asa ity; voatahiry byte-for-byte avokoa izy. Ny draft vaovao dia ilay exact sandbox text, tsy misy LF farany. Ny famerenana ara-piteny sy porofo rehetra teo aloha dia mihatra satria tsy niova ny lahatsoratra na reference na sary na rohy. Tsy misy fandikana vaovao na fanoloana asa hafa.\n')
        f.write('* Atao prepare sy fijerena preview vaovao alohan’ ny publish vaovao, miaraka amin’ ny baserevid sy digest vaovao. Tsy navahana na naleferina ny exact-hash guard; ny tanjona dia ny hanamarinana ny exact bytes efa hita, fa tsy ny hamerina write tsy fantatra vokatra.\n')
    write_json(NEW/'status.json',{'status':'rebased_after_confirmed_boundary_normalization',
        'prior_job':str(OLD),'inspected_revision':inspected['revision_id'],
        'exact_inspected_sha256':inspected['sha256'],'rebase_count':1})
    print('Single rebase ready:',NEW,'revision',inspected['revision_id'],inspected['sha256'])


if __name__=='__main__':
    main()
