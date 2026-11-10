"""Sequential guarded Wikipedia metadata and read-only terminology lookups."""
import re
from pathlib import Path

import mwparserfromhell as mw

from mgwiki_editor.core import GuardError, Wiki, lookup, now, read_json, write_json

JOB = Path('runs/baseball-20261106')
TERMS = [
    ('baseball','fanatanjahantena'), ('inning','fihodinana'), ('base','toby'),
    ('pitcher','mpanipy'), ('batter','mpikapoka'), ('catcher','mpisambotra'),
    ('out','fanesorana'), ('run','isa'), ('strike','kapoka'),
    ('ball','baolina'), ('home run','fihodinana'), ('bunt','kapoka'),
    ('pickoff','fanipazana'), ('balk','fandikan-dalàna'),
    ('fastball','haingana'), ('changeup','miadana'), ('curveball','miolaka'),
    ('slider','miolaka'), ('sabermetrics','antontanisa'),
    ('earned run','isa'), ('slugging percentage','tahan'),
    ('steroid','sterôida'), ('escapism','fialamboly'),
]


def main():
    e = JOB / 'evidence'
    e.mkdir(exist_ok=True)
    code = mw.parse((JOB/'source.wiki').read_text(encoding='utf-8'))
    inventory = [{'target':str(x.title),'label':str(x.text or x.title)} for x in code.filter_wikilinks()]
    for t in code.filter_templates():
        if str(t.name).strip().lower() in {'main','further','see also','anl','category see also'}:
            for p in t.params:
                if str(p.name).strip().isdigit():
                    inventory.append({'target':str(p.value).strip(),'label':str(p.value).strip()})
    write_json(JOB/'source-link-inventory.json', inventory)
    targets = sorted({x['target'].split('#')[0].replace('_',' ') for x in inventory
                      if ':' not in x['target'] and x['target']})
    files = sorted({x['target'].split(':',1)[1].strip() for x in inventory
                    if x['target'].lower().startswith(('file:','image:'))} |
                   {'Tommy Milone gives up a home run to Mike Trout on May 21, 2017.jpg',
                    'En-Baseball-article.ogg'})
    write_json(JOB/'source-file-inventory.json', files)
    wiki = Wiki()
    mapping = {}
    for start in range(0,len(targets),45):
        output = e/f'links-{start:03d}.json'
        if not output.exists():
            response = wiki.site('en').simple_request(
                action='query',prop='langlinks', titles='|'.join(targets[start:start+45]),
                lllang='mg',lllimit='max',formatversion=2,redirects=1,
            ).submit()
            write_json(output,{'retrieved_at':now(),'response':response})
            if 'continue' in response:
                raise GuardError('Continuation required; retained evidence')
        data = read_json(output)['response']
        for page in data['query']['pages']:
            mapping[page['title']] = {'mg':page.get('langlinks',[{}])[0].get('title'),
                                     'missing':page.get('missing',False),
                                     'evidence_file':str(output.relative_to(JOB))}
        for x in data.get('query',{}).get('redirects',[]) + data.get('query',{}).get('normalized',[]):
            if x['to'] in mapping:
                mapping[x['from']] = mapping[x['to']]
    write_json(JOB/'link-map.json',mapping)
    for filename, lang, params in [
        ('files.json','en',dict(prop='imageinfo',titles='|'.join('File:'+x for x in files),iiprop='timestamp|extmetadata')),
        ('categories.json','mg',dict(prop='info',titles='Sokajy:Fanatanjahantena|Sokajy:Baseball|Sokajy:Fanatanjahantena amin\'ny baolina')),
    ]:
        output=e/filename
        if not output.exists():
            response=wiki.site(lang).simple_request(action='query',formatversion=2,**params).submit()
            write_json(output,{'retrieved_at':now(),'response':response})
    # Verify actual local target identities and evidence for country-cache omissions.
    local=sorted({v['mg'] for v in mapping.values() if v.get('mg')})
    for start in range(0,len(local),45):
        output=e/f'local-{start:03d}.json'
        if not output.exists():
            response=wiki.site('mg').simple_request(action='query',prop='info|extracts',
                titles='|'.join(local[start:start+45]),exintro=1,explaintext=1,exsentences=1,
                formatversion=2).submit()
            write_json(output,{'retrieved_at':now(),'response':response})
    for english,malagasy in TERMS:
        for edition,word in [('en',english),('mg',malagasy)]:
            output=e/f'lookup-{edition}-{re.sub(r"[^a-z0-9]+","-",english)}.json'
            if output.exists():
                continue
            try:
                result=lookup(edition,word)
            except GuardError as exc:
                if any(x in str(exc).lower() for x in ('cooldown','deferred','circuit','rate','overload')):
                    raise
                result={'status':'failed','edition':edition,'word':word,'retrieved_at':now(),'error':str(exc)}
            write_json(output,result)
    print('Pinned',len(targets),'topics;',len(files),'files;',len(local),'local titles;',len(TERMS),'term pairs')


if __name__=='__main__':
    main()
