"""Single serialized guarded Wikipedia/dictionary worker. Never edits wikis."""
import argparse
from pathlib import Path

from mgwiki_editor.core import GuardError, Wiki, lookup, now, read_json, write_json

JOB = Path('runs/programming-language-20261109')


def metadata():
    e = JOB/'evidence'
    inventory = read_json(JOB/'source-link-inventory.json')
    targets = sorted({x['target'].split('#')[0].replace('_', ' ') for x in inventory
                      if ':' not in x['target'] and x['target']} | {'India', 'Japan'})
    files = sorted({x['target'] for x in inventory if x['target'].startswith('File:')})
    write_json(JOB/'source-file-inventory.json', files)
    wiki = Wiki()
    mapping = {}
    for start in range(0, len(targets), 45):
        output = e/f'links-{start:03}.json'
        if not output.exists():
            data = wiki.site('en').simple_request(action='query', prop='langlinks',
                  titles='|'.join(targets[start:start+45]), lllang='mg', lllimit='max',
                  formatversion=2, redirects=1).submit()
            write_json(output, {'retrieved_at':now(), 'response':data})
        data = read_json(output)['response']
        if 'continue' in data:
            raise GuardError('Metadata continuation required; retain partial evidence.')
        for page in data['query']['pages']:
            mapping[page['title']] = {'mg':page.get('langlinks',[{}])[0].get('title'),
                                     'missing':page.get('missing',False),
                                     'evidence_file':str(output.relative_to(JOB))}
        changes = data['query'].get('redirects',[]) + data['query'].get('normalized',[])
        for _ in range(len(changes)+1):
            for item in changes:
                if item['to'] in mapping:
                    mapping[item['from']] = mapping[item['to']]
    write_json(JOB/'link-map.json', mapping)
    for name,lang,params in [
      ('files.json','en',dict(prop='imageinfo',titles='|'.join(files),iiprop='timestamp|extmetadata')),
      ('local-titles.json','mg',dict(prop='info|extracts',titles='|'.join(sorted({v['mg'] for v in mapping.values() if v['mg']})),exintro=1,explaintext=1,exsentences=2)),
      ('categories.json','mg',dict(prop='info',titles='Sokajy:Kajimirindra|Sokajy:Solosaina|Sokajy:Fiteny fampandaharana')),
    ]:
        output=e/name
        if not output.exists():
            data=wiki.site(lang).simple_request(action='query',formatversion=2,**params).submit()
            write_json(output,{'retrieved_at':now(),'response':data})
    print('Metadata complete:',len(targets),'topics;',len(files),'files')


def dictionaries():
    terms=read_json(JOB/'term-inventory.json')
    e=JOB/'evidence'
    # Reuse exact language/word cached evidence; sense selection remains editorial.
    prior={}
    for f in Path('runs').rglob('lookup*.json'):
        if JOB in f.parents:
            continue
        try:
            d=read_json(f)
        except (ValueError,OSError):
            continue
        if isinstance(d,dict) and d.get('edition') in {'en','mg'} and d.get('word') and d.get('status') in {'found','missing','no_matching_language'}:
            prior[(d['edition'],d['word'])]=f
    seen={}
    for t in terms:
        for lang,word in [('en',t['source_term']),('mg',t.get('candidate_lookup',t['chosen_expression']))]:
            output=e/f"lookup-{lang}-{t['id']}.json"
            if output.exists():
                seen[(lang,word)]=output
                continue
            existing=seen.get((lang,word)) or prior.get((lang,word))
            if existing:
                output.write_bytes(existing.read_bytes())
            else:
                try:
                    d=lookup(lang,word)
                except GuardError as exc:
                    if any(x in str(exc).lower() for x in ('cooldown','deferred','circuit','rate','overload')):
                        raise
                    d={'edition':lang,'word':word,'status':'failed','retrieved_at':now(),'error':str(exc)}
                write_json(output,d)
            seen[(lang,word)]=output
    write_json(JOB/'dictionary-completion.json',{'status':'complete','at':now(),'term_count':len(terms)})
    print('Dictionary evidence complete:',len(terms),'senses')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['metadata','dictionary'])
    args=p.parse_args()
    (metadata if args.phase=='metadata' else dictionaries)()
