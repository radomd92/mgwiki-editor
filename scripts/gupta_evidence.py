"""Pinned Gupta link mapping; serial guarded requests only."""
import json
from pathlib import Path
import mwparserfromhell
from mgwiki_editor.core import Wiki

def main():
    p = Path('runs/gupta-empire-20261122')
    code = mwparserfromhell.parse((p/'source.wiki').read_text(encoding='utf-8'))
    targets = sorted({str(x.title).strip().split('#')[0] for x in code.filter_wikilinks() if str(x.title).strip() and not str(x.title).strip().lower().startswith(('file:', 'image:', ':file:', 'category:', '#'))})
    wiki = Wiki()
    mapping = {}
    for n in range(0,len(targets),50):
        dest=p/f'links-batch-{n//50}.json'
        if dest.exists():
            data=json.loads(dest.read_text(encoding='utf-8'))
        else:
            data=wiki.link_targets('en',targets[n:n+50])
            dest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        for page in data['response']['query']['pages']:
            mapping[page['title']] = next((x['title'] for x in page.get('langlinks',[]) if x['lang']=='mg'), None)
    (p/'link-map.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Done',len(mapping),'targets',sum(bool(x) for x in mapping.values()),'Malagasy')

if __name__ == '__main__':
    main()
