"""Targeted, serialized evidence and reusable vocabulary selection."""
from pathlib import Path
from urllib.parse import unquote
import shutil

from mgwiki_editor.core import Wiki, lookup, GuardError, now, read_json, write_json

J=Path('runs/achilles-20261107')


def main():
    w=Wiki(); d=J/'evidence'
    p=d/'local-topic-pages.json'
    if not p.exists():
        titles=['Achille','Angano grika','Iliada','Iliasy','Iliady','Aotrisy','Ôtrisy','Aotrisia','Biôgrafia','Trôia','Sokajy:Angano grika']
        data=w.site('mg').simple_request(action='query',prop='revisions',titles='|'.join(titles),rvprop='ids|content',rvslots='main',formatversion=2).submit()
        write_json(p,dict(retrieved_at=now(),response=data))
    p=d/'decoded-file.json'
    if not p.exists():
        files=read_json(J/'source-image-inventory.json')
        name=next(f for f in files if '%' in f)
        data=w.site('en').simple_request(action='query',prop='imageinfo',titles='File:'+unquote(name),iiprop='timestamp|extmetadata',formatversion=2).submit()
        write_json(p,dict(retrieved_at=now(),source_filename=name,response=data))
    # Reuse exact sense lookups, not earlier editorial choices.
    terms=[('epic','tononkalo'),('kleos','voninahitra'),('plague','valanaretina'),('scholium','fanamarihana'),('epithet','anarana'),('oracle','mpaminany'),('patronymic','anarana')]
    for en,mg in terms:
        for edition in ['en','mg']:
            matches=list(Path('runs/iliad-en-20261106/evidence').glob(f'lookup-{edition}-{en}.json'))+list(Path('runs/oedipus-20261105/evidence').glob(f'lookup-{edition}-{en}.json'))
            if matches: shutil.copyfile(matches[0],d/f'lookup-{edition}-{en}.json')
    fresh=[('invulnerable','maratra'),('hero cult','fivavahana'),('centaur','kentao'),('Nereid','andriamanibavy'),('tendon','hozatra'),('dative','anarana'),('palatalization','lanilany'),('pederasty','firaisana'),('votive','fanatitra'),('tumulus','fasana'),('temenos','toerana'),('libretto','tononkira'),('oinochoe','siny'),('kylix','kaopy'),('lekythos','tavoahangy'),('cruiser','sambo')]
    for en,mg in fresh:
        for ed,word in [('en',en),('mg',mg)]:
            p=d/f'lookup-{ed}-{en.replace(" ","-")}.json'
            if p.exists(): continue
            try: result=lookup(ed,word)
            except GuardError as e:
                result=dict(status='failed',edition=ed,word=word,retrieved_at=now(),error=str(e))
                write_json(p,result)
                if 'cooldown' in str(e).lower() or 'defer' in str(e).lower(): raise
                continue
            write_json(p,result)
    print('Targeted evidence pinned')


if __name__=='__main__': main()
