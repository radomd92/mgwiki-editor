"""Read-only bounded Gupta metadata through shared Wiki gateway."""
import json
import re
from pathlib import Path
import mwparserfromhell
from mgwiki_editor.core import Wiki

p=Path('runs/gupta-empire-20261122')
s=(p/'source.wiki').read_text(encoding='utf-8')
files={str(x.title).split(':',1)[1].strip() for x in mwparserfromhell.parse(s).filter_wikilinks() if str(x.title).strip().lower().startswith(('file:','image:',':file:')) and not str(x.title).startswith(':')}
for line in s.splitlines():
    if re.match(r'(?:File:)?[^|\[\]]+\.(?:jpg|tif|png|JPG)\|',line):
        files.add(line.split('|')[0].removeprefix('File:'))
files.update(['South Asia historical AD375 EN.svg','South Asia historical AD450 EN.svg','Map of the Gupta Empire circa 420 CE.png','Meister_des_Mahâjanaka_Jâtaka_001.jpg','Allahabad stone pillar inscription of Samudragupta.jpg'])
wiki=Wiki()
def save(name,data):
    (p/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    if not (p/'source-templates.json').exists():
        data=wiki.site('en').simple_request(action='query',titles='Template:South Asia in 600 CE|Template:British-Museum-db|Template:EB1911 poster|Template:Infobox country',prop='revisions',rvprop='ids|content',rvslots='main',formatversion=2).submit()
        save('source-templates.json',data)
    save('local-templates.json',wiki.site('mg').simple_request(action='query',titles='Template:Infobox country|Template:Infobox former country|Template:lahatsoratra antsipirihany|Template:Cite book|Template:Sfn',prop='revisions',rvprop='ids|content',rvslots='main',formatversion=2).submit())
    save('local-categories.json',wiki.site('mg').simple_request(action='query',titles='Sokajy:Tantaran\' i India|Sokajy:India|Sokajy:Empira',prop='info',formatversion=2).submit())
    for n in range(0,len(files),30):
        batch=sorted(files)[n:n+30]
        save(f'file-metadata-{n//30}.json',{'requested':batch,'response':wiki.site('mg').simple_request(action='query',titles='|'.join('File:'+f for f in batch),prop='imageinfo',iiprop='url|timestamp|sha1|extmetadata',formatversion=2).submit()})
    print('Metadata done',len(files),'files')

if __name__ == '__main__':
    main()
