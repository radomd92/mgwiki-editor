"""Inspect prepared HTML offline; never fetch linked media, styles or references."""
from pathlib import Path
import re
from bs4 import BeautifulSoup
from mgwiki_editor.core import read_json,write_json

JOB=Path('runs/mahabharata-20261108')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job',type=Path,default=JOB)
    JOB=parser.parse_args().job
    html=(JOB/'preview.html').read_text(encoding='utf-8')
    soup=BeautifulSoup(html,'html.parser')
    headings=[x.get_text(' ',strip=True) for x in soup.select('h2,h3')]
    images=[dict(alt=x.get('alt',''),src=x.get('src','')) for x in soup.find_all('img')]
    tables=[]
    for table in soup.find_all('table'):
        rows=[]
        for row in table.find_all('tr',recursive=True):
            rows.append([cell.get_text(' ',strip=True) for cell in row.find_all(['th','td'],recursive=False)])
        tables.append(rows)
    anchors={x.get('id') for x in soup.find_all(id=True)}
    broken=[x.get('href') for x in soup.select('a[href^="#"]') if x.get('href')[1:] not in anchors]
    stats=dict(headings=headings,images=images,table_rows=[len(t) for t in tables],
               reference_entries=len(soup.select('li[id^="cite_note"]')),broken_local_anchors=broken,
               parser_errors=[x.get_text(' ',strip=True) for x in soup.select('.error,.mw-ext-cite-error')],
               internal_redlinks=[x.get('title') for x in soup.select('a.new')],
               external_links=len(soup.select('a.external')))
    write_json(JOB/'offline-preview-audit.json',stats)
    text=soup.get_text(' ',strip=True)
    # Whitespace/layout review follows the actual parsed blocks, not a new render.
    blocks=[]
    for node in soup.find_all(['h2','h3','p','table','blockquote','figcaption','ol']):
        if node.find_parent(['table','blockquote','ol']) is not None: continue
        blocks.append(node.get_text(' ',strip=True))
    (JOB/'offline-preview-text.txt').write_text('\n\n'.join(blocks),encoding='utf-8')
    (JOB/'offline-preview-tables.txt').write_text('\n\n'.join('TABLE '+str(i+1)+'\n'+'\n'.join(' || '.join(r) for r in rows) for i,rows in enumerate(tables)),encoding='utf-8')
    print('OFFLINE AUDIT', {k:v for k,v in stats.items() if k not in {'headings','images'}})
    print('HEADINGS\n'+'\n'.join(headings))
    print('IMAGE ALTS\n'+'\n'.join(x['alt'] for x in images))
    print('LEAD\n'+text[:4200])
    for phrase in ['Mazava ho azy fa tononkalo', 'faha-11 sy faha-12', 'Tetiaran', 'Fanamarihana manazava', 'Rohy ivelany']:
        pos=text.find(phrase)
        print('\nEXCERPT '+phrase+'\n'+text[max(0,pos-80):pos+1500])
    print('\nBIBLIOGRAPHY AND END\n'+text[-9000:])
