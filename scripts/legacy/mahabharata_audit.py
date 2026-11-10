"""Serial guarded Wikipedia evidence for material source anomalies."""
from pathlib import Path
from mgwiki_editor.core import Wiki, now, write_json, read_json

JOB=Path('runs/mahabharata-20261108')

if __name__=='__main__':
    d=JOB/'evidence'; d.mkdir(exist_ok=True)
    wiki=Wiki()
    p=d/'historical-source-2020.json'
    if p.exists():
        data=read_json(p)['response']
    else:
        data=wiki.site('en').simple_request(action='query',titles='Mahabharata',
            prop='revisions',rvstart='2020-05-01T00:00:00Z',rvdir='older',rvlimit=1,
            rvprop='ids|timestamp|comment|content',rvslots='main',formatversion=2).submit()
        write_json(p,dict(retrieved_at=now(),response=data))
    text=data['query']['pages'][0]['revisions'][0]['slots']['main']['content']
    (d/'historical-source-2020.wiki').write_text(text)
    data=wiki.site('en').simple_request(action='query',titles='Rashmirathi|Ramdhari Singh Dinkar|Urvashi (poem)',
        prop='revisions',rvprop='ids|timestamp|content',rvslots='main',formatversion=2).submit()
    write_json(d/'award-topic-evidence.json',dict(retrieved_at=now(),response=data))
    for page in data['query']['pages']:
        if 'revisions' in page:
            (d/(page['title'].replace(' ','_')+'.wiki')).write_text(page['revisions'][0]['slots']['main']['content'])
    data=wiki.site('en').simple_request(action='query',titles='Template:Kuru family tree',
        prop='revisions',rvlimit=1,rvprop='ids|timestamp|content',rvslots='main',formatversion=2).submit()
    write_json(d/'kuru-tree.json',dict(retrieved_at=now(),response=data))
    (d/'kuru-tree.wiki').write_text(data['query']['pages'][0]['revisions'][0]['slots']['main']['content'])
    print('Pinned historical source, award pages, and family-tree template.')
