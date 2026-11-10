"""Serialized read-only dictionary checks, reusing earlier exact lookup evidence."""
from pathlib import Path
import shutil

from mgwiki_editor.core import lookup, GuardError, now, read_json, write_json

J=Path('runs/achilles-20261107')
TERMS=[('fresco','hosodoko'),('loanword','teny'),('trilogy','telo'),
 ('engraving','sokitra'),('lithography','vato'),('oratorio','hira'),
 ('ballad opera','hira'),('sarcophagus','vatam-paty'),('stela','tsangambato'),
 ('heroön','fasana'),('monogram','litera'),('tondo','boribory'),
 ('illuminated manuscript','sora-tanana'),('acropolis','havoana'),
 ('villa','trano'),('platonic','fitiavana'),('heterosexual','fitiavana'),
 ('homosexual','fitiavana'),('philia','fisakaizana'),('funeral games','fandevenana'),
 ('muster','tafika'),('ambrosia','sakafo'),('tragedy','tantara'),
 ('chorus','mpihira'),('paradox','hevitra'),('armour','fiadiana'),
 ('archaic','taloha'),('gladiator','mpiady')]


def main():
    cached={}
    for p in sorted(Path('runs').glob('*/evidence/lookup*.json')):
        try:a=read_json(p)
        except (ValueError,OSError):continue
        if a.get('edition') in {'en','mg'} and a.get('word'):
            key=(a['edition'],a['word'])
            if a.get('status')=='found' or key not in cached:cached[key]=p
    for en,mg in TERMS:
        for ed,word in [('en',en),('mg',mg)]:
            p=J/'evidence'/f'lookup-{ed}-{en.replace(" ","-")}.json'
            if p.exists():continue
            old=cached.get((ed,word))
            if old:
                shutil.copyfile(old,p)
                continue
            try:result=lookup(ed,word)
            except GuardError as e:
                result=dict(status='failed',edition=ed,word=word,retrieved_at=now(),error=str(e))
                write_json(p,result)
                if 'cooldown' in str(e).lower() or 'defer' in str(e).lower():raise
                continue
            write_json(p,result)
    print('Remaining terminology checks pinned')


if __name__=='__main__':main()
