"""Guarded clarification of material source wording and pottery senses."""
from pathlib import Path
from mgwiki_editor.core import Wiki, lookup, GuardError, now, write_json

J=Path('runs/achilles-20261107')


def main():
    w=Wiki();d=J/'evidence'
    p=d/'troilus-name-clarification.json'
    if not p.exists():
        data=w.site('en').simple_request(action='query',prop='extracts',titles='Cressida|Chryseis|Troilus and Criseyde',exintro=True,explaintext=True,formatversion=2).submit()
        write_json(p,dict(retrieved_at=now(),response=data))
    for en,mg in [('omphalos','vato'),('red-figure','tanimanga'),('black-figure','tanimanga'),('hydria','siny'),('kantharos','kaopy'),('krater','siny'),('mosaic','môzaika'),('oenochoe','siny'),('spit','tany'),('monism','fampianarana')]:
        for edition,word in [('en',en),('mg',mg)]:
            p=d/f'lookup-{edition}-{en}.json'
            if p.exists():continue
            try: result=lookup(edition,word)
            except GuardError as exc:
                result=dict(status='failed',edition=edition,word=word,retrieved_at=now(),error=str(exc))
                write_json(p,result)
                if 'cooldown' in str(exc).lower() or 'defer' in str(exc).lower():raise
                continue
            write_json(p,result)
    print('Clarification evidence preserved')


if __name__=='__main__':main()
