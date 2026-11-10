"""Read specifically needed Wikipedia source context via guarded Wiki."""
import json
from pathlib import Path

from mgwiki_editor.core import Wiki

J=Path('runs/alina-iraika-20261105')


def main():
    wiki=Wiki()
    tasks=[('qahramana','Qahramana'),('tezuka','Osamu Tezuka'),
           ('yamamoto','Eiichi Yamamoto'),('hoshino','Yukinobu Hoshino'),
           ('manhwa','One Thousand and One Nights (manhwa)')]
    for ident,title in tasks:
        f=J/('identity-'+ident+'.json')
        if f.exists():
            continue
        data=wiki.site('en').simple_request(action='parse',page=title,section=0,
             prop='wikitext',formatversion=2).submit()
        f.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    f=J/'earlier-source.json'
    if not f.exists():
        data=wiki.site('en').simple_request(action='query',prop='revisions',
             titles='One Thousand and One Nights',rvstart='2025-01-01T00:00:00Z',
             rvlimit=1,rvprop='ids|timestamp|content',rvslots='main',formatversion=2).submit()
        f.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
