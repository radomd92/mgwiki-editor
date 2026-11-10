"""One explicit rebase, retaining all accepted sections and fresh init state."""
import json
import shutil
from pathlib import Path

OLD=Path('runs/alina-iraika-20261105')
NEW=Path('runs/alina-iraika-20261105-r1')


def main():
    a=(OLD/'source.wiki').read_text(encoding='utf-8')
    b=(NEW/'source.wiki').read_text(encoding='utf-8')
    before='access-date=29 November 2026'
    after='access-date=29 October 2026'
    assert a.count(before)==1 and a.replace(before,after)==b
    for n in ('existing.wiki','sandbox.wiki'):
        assert (OLD/n).read_bytes()==(NEW/n).read_bytes()==b''
    excluded={'job.json','source.wiki','existing.wiki','sandbox.wiki','review.json','proposal.json','preview.html','changes.diff','receipt.json'}
    for f in OLD.iterdir():
        if f.name in excluded:
            continue
        if f.is_dir():
            shutil.copytree(f,NEW/f.name,dirs_exist_ok=False)
        else:
            shutil.copyfile(f,NEW/f.name)
    source=NEW/'sections/06-manuscripts/source.wiki'
    text=source.read_text(encoding='utf-8')
    assert text.count(before)==1
    source.write_text(text.replace(before,after),encoding='utf-8')
    plan=json.loads((NEW/'section-plan.json').read_text(encoding='utf-8'))
    at=a.index(before)
    delta=len(after)-len(before)
    for row in plan:
        row['directory']=row['directory'].replace(str(OLD),str(NEW))
        for key in ('source_start','source_end'):
            if row[key]>at:
                row[key]+=delta
        if row['id']=='06-manuscripts':
            row['status']='pending_targeted_metadata_correction'
    (NEW/'section-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    status={'status':'superseded_source_changed_no_save','rebase_job':str(NEW),'reason':'Source revision changed; exactly one access-date correction, November to October.'}
    (OLD/'status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
    notes=(NEW/'notes.wiki').read_text(encoding='utf-8')
    notes+='\n== Fanavaozana indray mandeha noho ny fiovan’ ny loharano ==\n'
    notes+='Tsy nisy save natao tamin’ ny job voalohany. Ny loharano vaovao dia [https://en.wikipedia.org/w/index.php?oldid=1383933346 fanitsiana 1383933346]. Nampitahaina manontolo tamin’ ny 1383561034 izy io: mitovy tanteraka ny soratra rehetra afa-tsy ny access-date iray, 29 November 2026 → 29 October 2026, ao amin’ ny fizarana sora-tanana. Ny source-rebase.diff no mitahiry ny fampitahana feno. Voavaky ilay fiovana sy ny manodidina azy; ny ambiny dia ilay soratra efa voavaky manontolo, voamarina ho mitovy tsirairay. Mbola foana ny existing sy sandbox vaovao. Notazonina avokoa ireo fizarana 37 efa vita; ny metadata ao amin’ ny 06-manuscripts ihany no nomena fanitsiana voatokana. Tsy nisy famoronana lahatsoratra manontolo indray na fanitsiana mainspace.\n'
    (NEW/'notes.wiki').write_text(notes,encoding='utf-8')


if __name__=='__main__':
    main()
