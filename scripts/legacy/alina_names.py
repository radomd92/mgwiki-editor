"""Pin missing local country naming and broadcasting identity evidence."""
import json
from pathlib import Path

from mgwiki_editor.core import Wiki

J=Path('runs/alina-iraika-20261105')


def main():
    w=Wiki()
    for ident,title in [('usa','Etazonia'),('china','Sina'),('mexico','Meksika'),('austria','Aotrisy')]:
        path=J/('country-'+ident+'.json')
        if path.exists():
            continue
        if ident=='china':
            data=w.site('mg').simple_request(action='query',prop='revisions',titles=title,
                rvprop='ids|content',rvslots='main',formatversion=2).submit()
        else:
            data=w.snapshot('mg',title)
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    for ident,title in [('bbc','BBC'),('dd','DD National'),('upa','United Productions of America')]:
        path=J/('identity-'+ident+'.json')
        if path.exists():
            continue
        data=w.site('en').simple_request(action='parse',page=title,section=0,prop='wikitext',formatversion=2).submit()
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
