"""Pin missing country identities and focused supplementary article evidence."""
from pathlib import Path

from mgwiki_editor.core import Wiki, now, write_json

JOB=Path('runs/baseball-20261106')


def main():
    wiki=Wiki();e=JOB/'evidence'
    names='Mexico|Venezuela|Netherlands|Brazil|Argentina|Peru|Costa Rica|Dominican Republic|Philippines|South Korea|Cuba|Taiwan|China|United Kingdom|North America|Latin America'
    output=e/'additional-countries-en.json'
    if not output.exists():
        response=wiki.site('en').simple_request(action='query',prop='langlinks',titles=names,
            lllang='mg',lllimit='max',formatversion=2).submit()
        write_json(output,{'retrieved_at':now(),'response':response})
    for name in ['Major League Baseball rosters','Designated hitter']:
        output=e/(name.replace(' ','-')+'.json')
        if not output.exists():
            snap=wiki.snapshot('en',name)
            write_json(output,snap)
            output.with_suffix('.wiki').write_text(snap['text'],encoding='utf-8')
    data=__import__('json').loads((e/'additional-countries-en.json').read_text(encoding='utf-8'))
    local=[p['langlinks'][0]['title'] for p in data['response']['query']['pages'] if p.get('langlinks')]
    output=e/'additional-countries-mg.json'
    if not output.exists():
        response=wiki.site('mg').simple_request(action='query',prop='info|extracts',
            titles='|'.join(local),exintro=1,explaintext=1,formatversion=2).submit()
        write_json(output,{'retrieved_at':now(),'response':response})
    print('Supplement pinned')


if __name__=='__main__':
    main()
