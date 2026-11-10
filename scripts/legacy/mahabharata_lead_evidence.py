"""Preserve limited terminology and lead metadata for the blocked translation."""
from pathlib import Path
import shutil
import mwparserfromhell as mw
from mgwiki_editor.core import Wiki, lookup, now, write_json, read_json

JOB=Path('runs/mahabharata-20261108')


if __name__=='__main__':
    d=JOB/'evidence'; d.mkdir(exist_ok=True)
    pairs=[('epic','epika'),('couplet','andalana'),('prose','lahatsoratra'),
           ('smriti','lovantsofina'),('itihasa','tantara'),('dharma','adidy'),
           ('purushartha','tanjona'),('shloka','andininy')]
    # Reuse recent successful lookup files, not unsupported remembered labels.
    for en,mg in pairs:
        for edition,word in [('en',en),('mg',mg)]:
            dest=d/f'lookup-{edition}-{word}.json'
            if dest.exists():
                continue
            candidates=list(Path('runs').glob(f'*/lookup-{edition}-{word}.json'))
            used=False
            for p in candidates:
                data=read_json(p)
                if data.get('status') in {'found','missing','no_matching_language'}:
                    shutil.copyfile(p,dest)
                    used=True
                    break
            if not used:
                try:
                    data=lookup(edition,word)
                except Exception as exc:
                    data=dict(edition=edition,word=word,status='lookup_failed',
                              retrieved_at=now(),error=type(exc).__name__,message=str(exc))
                write_json(dest,data)
            print(dest.name,read_json(dest).get('status'),flush=True)
    wiki=Wiki()
    text=(JOB/'sections/00-lead/source.wiki').read_text(encoding='utf-8')
    targets=sorted({str(l.title).split('#')[0].strip() for l in mw.parse(text).filter_wikilinks()
                    if ':' not in str(l.title)})
    p=d/'lead-links.json'
    if not p.exists():
        data=wiki.site('en').simple_request(action='query',prop='langlinks',
            titles='|'.join(targets),lllang='mg',lllimit='max',formatversion=2).submit()
        write_json(p,dict(retrieved_at=now(),response=data))
    mapping={}
    data=read_json(p)['response']
    if 'continue' in data:
        raise RuntimeError('Unprocessed continuation')
    for page in data['query']['pages']:
        mapping[page['title']]=dict(mg=page.get('langlinks',[{}])[0].get('title'),
                                   evidence_file='evidence/lead-links.json')
    for item in data['query'].get('normalized',[]):
        if item['to'] in mapping:
            mapping[item['from']]=mapping[item['to']]
    write_json(JOB/'link-map.json',mapping)
    p=d/'lead-images.json'
    if not p.exists():
        data=wiki.site('en').simple_request(action='query',prop='imageinfo',
            titles='File:Kurukshetra.jpg|File:Krishna and Arjun on the chariot, Mahabharata, 18th-19th century, India.jpg',
            iiprop='timestamp|extmetadata',formatversion=2).submit()
        write_json(p,dict(retrieved_at=now(),response=data))
