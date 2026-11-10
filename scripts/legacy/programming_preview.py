"""Read rendered HTML offline only; never load URLs or browser resources."""
import textwrap
from collections import Counter
from html.parser import HTMLParser

import mwparserfromhell as mw

from mgwiki_editor.core import digest, read_json, write_json
from programming_plan import JOB


class Preview(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text=[];self.images=[];self.links=[];self.ids=[];self.references=[]
        self.skip=0;self.errors=[]

    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ['script','style']:
            self.skip+=1
        if a.get('id'):
            self.ids.append(a['id'])
        if tag=='img':
            self.images.append(a)
        if tag=='a':
            self.links.append(a)
        if tag=='li' and a.get('id','').startswith('cite_note-'):
            self.references.append(a['id'])
        if 'error' in a.get('class','').split() or 'mw-ext-cite-error' in a.get('class',''):
            self.errors.append(a)
        if tag in ['p','div','li','br','h2','h3','h4','pre','tr']:
            self.text.append('\n')

    def handle_endtag(self,tag):
        if tag in ['script','style']:
            self.skip=max(0,self.skip-1)
        if tag in ['p','li','h2','h3','h4','pre','tr']:
            self.text.append('\n')

    def handle_data(self,data):
        if not self.skip:
            self.text.append(data)


if __name__=='__main__':
    raw=(JOB/'preview.html').read_text(encoding='utf-8')
    p=Preview();p.feed(raw)
    lines=[' '.join(x.split()) for x in ''.join(p.text).splitlines() if x.strip()]
    (JOB/'preview-readable.txt').write_text('\n'.join(textwrap.fill(x,140,break_long_words=False,break_on_hyphens=False) for x in lines)+'\n',encoding='utf-8')
    code=mw.parse((JOB/'draft.wiki').read_text(encoding='utf-8'))
    anonymous=0;named=set()
    for tag in code.filter_tags():
        if str(tag.tag).lower()=='ref' and not tag.self_closing:
            if tag.has('name'):
                named.add(str(tag.get('name').value).strip('\"\' '))
            else:
                anonymous+=1
    report={'proposal_digest':read_json(JOB/'proposal.json')['digest'],
            'preview_sha256':digest(raw.encode('utf-8')),'images':p.images,
            'duplicate_ids':[x for x,n in Counter(p.ids).items() if n>1],
            'rendered_reference_count':len(p.references),'expected_reference_count':anonymous+len(named),
            'error_elements':p.errors,'links':p.links,'network_resources_loaded':False,
            'inspection':'offline extraction only; coordinator visual text/markup review pending'}
    write_json(JOB/'preview-metadata.json',report)
    print('Images:',len(p.images),'References:',len(p.references),'Expected:',anonymous+len(named),
          'Duplicate IDs:',report['duplicate_ids'],'Errors:',len(p.errors))
