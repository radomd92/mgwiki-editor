"""Final serialized local-target and descriptive art-term checks."""
from pathlib import Path
from mgwiki_editor.core import Wiki, lookup, GuardError, now, read_json, write_json

J=Path('runs/achilles-20261107')


def main():
    w=Wiki();d=J/'evidence'
    targets=sorted({x['mg'] for x in read_json(J/'link-map.json').values() if x.get('mg')})
    for start in range(0,len(targets),45):
        p=d/f'local-link-verification-{start:03}.json'
        if not p.exists():
            data=w.site('mg').simple_request(action='query',prop='info|pageprops',ppprop='disambiguation',titles='|'.join(targets[start:start+45]),formatversion=2).submit()
            write_json(p,dict(retrieved_at=now(),response=data))
    for en,mg in [('light novel','tantara'),('pastel','loko'),('amber','ditin-kazo')]:
        for ed,word in [('en',en),('mg',mg)]:
            p=d/f'lookup-{ed}-{en.replace(" ","-")}.json'
            if p.exists():continue
            try:r=lookup(ed,word)
            except GuardError as e:
                r=dict(status='failed',word=word,edition=ed,retrieved_at=now(),error=str(e))
                write_json(p,r)
                if 'cooldown' in str(e).lower() or 'defer' in str(e).lower():raise
                continue
            write_json(p,r)
    print('Final evidence pinned')


if __name__=='__main__':main()
