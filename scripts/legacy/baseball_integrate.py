"""Coordinator-only offline integration of section handoffs and pinned evidence."""
import re
import textwrap
from pathlib import Path

import mwparserfromhell as mw

from genji_en_native import native_templates
from mgwiki_editor.core import read_json, write_json

JOB=Path('runs/baseball-20261106')
COUNTRIES={'England':'Angletera','United States':'Etazonia','Canada':'Kanada',
 'Mexico':'Meksika','Venezuela':'Venezoela','Netherlands':'Nederlandy','Brazil':'Brezila',
 'Argentina':'Arzantina','Peru':'Però','Costa Rica':'Kôsta Rika',
 'Dominican Republic':'Repoblika Dôminikana','Philippines':'Filipina','Thailand':'Tailandy',
 'South Sudan':'Sodàna Atsimo','Britain':'Britaina Lehibe','Wales':'Kambria'}


def normalize_text(text):
    # Never normalize work titles/retained foreign names inside italic spans.
    parts=re.split(r"(''.*?'')",text,flags=re.S)
    for i in range(0,len(parts),2):
        for en,mg in sorted(COUNTRIES.items(),key=lambda x:-len(x[0])):
            parts[i]=re.sub(r'(?<!\w)'+re.escape(en)+r'(?!\w)',mg,parts[i])
        parts[i]=parts[i].replace('steroida','sterôida')
    return ''.join(parts)


def walk_text(code, callback):
    for node in list(code.nodes):
        if isinstance(node,mw.nodes.Text):
            changed=callback(str(node))
            if changed!=str(node):
                code.replace(node,changed,recursive=False)
        elif isinstance(node,mw.nodes.Tag):
            if str(node.tag).lower() not in {'ref','nowiki','references','math','code'} and node.contents:
                walk_text(node.contents,callback)
        elif isinstance(node,mw.nodes.Heading):
            walk_text(node.title,callback)


def mapping():
    result=read_json(JOB/'link-map.json')
    for page in read_json(JOB/'evidence/additional-countries-en.json')['response']['query']['pages']:
        if page.get('langlinks'):
            result[page['title']]={'mg':page['langlinks'][0]['title'],
                'evidence_file':'evidence/additional-countries-en.json'}
    result['Netherlands']={'mg':'Nederlandy','evidence_file':'evidence/netherlands-local.json'}
    result['North America']={'mg':'Amerika Avaratra','evidence_file':'evidence/netherlands-local.json'}
    for key in ['Cleveland','Cleveland, Ohio']:
        result[key]={'mg':None,'rejected_mg':'Cleveland','reason':'Pinned local extract identifies Queensland, Australia, not Ohio',
                     'evidence_file':'evidence/local-000.json'}
    write_json(JOB/'resolved-link-map.json',result)
    return result


def adapt(text,linkmap,normalize=True):
    text=native_templates(text,{'!':'&#124;','update inline':''})
    code=mw.parse(text)
    verified={v['mg'] for v in linkmap.values() if v.get('mg')}
    decisions=[]
    for link in list(code.filter_wikilinks()):
        target=str(link.title).strip();base,_,anchor=target.partition('#')
        if target.lower().startswith(('file:','image:','media:',':sokajy:')):
            if link.text:
                caption,ds=adapt(str(link.text),linkmap,normalize)
                link.text=caption;decisions+=ds
            continue
        label=str(link.text) if link.text is not None else target
        # Only newly translated link labels are normalized, never exact targets.
        if normalize and not label.startswith("''"):
            label=normalize_text(label)
        if target.startswith('#'):
            continue
        if base in verified:
            replacement=f'[[{base}|{label}]]' if label!=base else f'[[{base}]]'
        else:
            mg=linkmap.get(base.replace('_',' '),{}).get('mg')
            replacement=(f'[[{mg}|{label}]]' if label!=mg else f'[[{mg}]]') if mg else label
            decisions.append(target+' → '+(mg or 'soratra tsotra: tsy misy kendrena mitovy lohahevitra voamarina'))
        try:
            code.replace(link,replacement)
        except ValueError:
            pass
    if normalize:
        walk_text(code,normalize_text)
    return str(code),decisions


def restore_verified(text,linkmap):
    # Some workers correctly used plain-text fallbacks before metadata arrived.
    # Restore same-topic verified proper names only; do not infer unverified targets.
    aliases={}
    for en,item in linkmap.items():
        mg=item.get('mg')
        if not mg or len(en)<4 or ':' in en or en in {'Sport','sport','Statistics','statistics'}:
            continue
        if '(' not in en and '#' not in en:
            aliases[normalize_text(en)]=mg
        if len(mg)>3:
            aliases[mg]=mg
    aliases.pop('Cleveland',None)
    aliases.pop('George Bush',None)  # Keep documented W. in prose, target only via source mapping.
    code=mw.parse(text)
    for link in list(code.filter_wikilinks(recursive=False)):
        if str(link.title).lower().startswith(('file:','image:')) and link.text:
            link.text=restore_verified(str(link.text),linkmap)
    seen=set()
    pattern=re.compile(r'(?<![\w])('+ '|'.join(re.escape(k) for k in sorted(aliases,key=len,reverse=True))+r')(?![\w])')
    def replace(s):
        chunks=re.split(r"(''.*?'')",s,flags=re.S)
        def sub(m):
            label=m[0];target=aliases[label]
            if target in seen:
                return label
            seen.add(target)
            return f'[[{target}|{label}]]' if target!=label else f'[[{target}]]'
        for i in range(0,len(chunks),2):
            chunks[i]=pattern.sub(sub,chunks[i])
        return ''.join(chunks)
    walk_text(code,replace)
    return str(code)


def main():
    plan=read_json(JOB/'section-plan.json');linkmap=mapping()
    pieces=[];notes=[];vocab=[];decisions=[]
    for item in plan:
        d=Path(item['directory'])
        for name in ['section.wiki','notes.wiki','vocabulary.json']:
            if not (d/name).is_file():raise RuntimeError('Missing '+str(d/name))
        raw=(d/'section.wiki').read_text(encoding='utf-8')
        if not raw.strip():raise RuntimeError('Empty section '+item['id'])
        text,ds=adapt(raw,linkmap,normalize=item['id']!='24-bibliography');decisions += [item['id']+': '+s for s in ds]
        text=restore_verified(text,linkmap)
        pieces.append(text.strip())
        notes.append('\n== '+item['id']+' ==\n'+(d/'notes.wiki').read_text(encoding='utf-8'))
        records=read_json(d/'vocabulary.json')
        if isinstance(records,dict):records=records.get('terms',records.get('entries',[]))
        for rec in records:
            rec['section_id']=item['id']
            files=rec.setdefault('evidence_files',[])
            files.append('sections/'+item['id']+'/source.wiki')
            vocab.append(rec)
        item['status']='integrated_pending_coordinator_review'
    text='\n\n'.join(pieces)+'\n'
    text=text.replace('{{!}}','&#124;')
    text=text.replace('dia noraran\' io fikambanana io tsy handray anjara ny Amerikanina mainty hoditra.',
        'dia noraran\' io fikambanana io tsy handray anjara ny [[Afrikana-Amerikana|Amerikanina mainty hoditra]].')
    text=text.replace('Mora ampiharana antontanisa kokoa noho',
        'Mora ampiharana [[Statistika|antontanisa]] kokoa noho',1)
    # Restore source reference definitions ONLY where retained claims call them.
    refs=read_json(JOB/'reference-definitions.json')
    code=mw.parse(text);used=set();defined=set()
    for tag in code.filter_tags():
        if str(tag.tag).lower()=='ref' and tag.has('name'):
            name=str(tag.get('name').value).strip('"\' ')
            group=str(tag.get('group').value).strip('"\' ') if tag.has('group') else ''
            (used if tag.self_closing else defined).add(group+'|'+name)
    definitions=[]
    for key in sorted(used-defined):
        if key not in refs:raise RuntimeError('Undefined '+key)
        item=refs[key]
        body,ds=adapt(item['body'],linkmap,normalize=False);decisions+=ds
        body=body.replace('{{!}}','&#124;')
        definitions.append(f'<ref name="{item["name"]}">'+body+'</ref>')
    text=text.replace('<references />','<references>\n'+'\n'.join(definitions)+'\n</references>',1)
    text+='\n[[:Sokajy:Baseball]]\n'
    (JOB/'draft.wiki').write_text(text,encoding='utf-8')
    (JOB/'section-handoffs.wiki').write_text('\n'.join(notes),encoding='utf-8')
    (JOB/'link-decisions.wiki').write_text('= Fanapahan-kevitra momba ny rohy =\n'+'\n'.join('* '+s for s in decisions)+'\n',encoding='utf-8')
    write_json(JOB/'integrated-section-plan.json',plan)
    write_json(JOB/'vocabulary.json',vocab)
    # Raw reading aid is offline only and does not replace the exact article artifact.
    (JOB/'draft-readable.txt').write_text('\n'.join('\n'.join(textwrap.wrap(l,160,replace_whitespace=False,drop_whitespace=False,break_long_words=False,break_on_hyphens=False)) for l in text.splitlines())+'\n',encoding='utf-8')
    print('Integrated',len(plan),'sections',len(text.encode('utf-8')),'bytes;',len(used),'reference names')
    print('Remaining templates:',[str(t.name) for t in mw.parse(text).filter_templates()])


if __name__=='__main__':
    main()
