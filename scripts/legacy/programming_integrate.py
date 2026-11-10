"""Offline coordinator integration, native citations, and explicit link accounting."""
import re
import textwrap
from pathlib import Path

import mwparserfromhell as mw

from genji_en_native import citation, param
from mgwiki_editor.core import read_json, write_json
from programming_plan import JOB

OMIT = {'short description', 'pp-pc1', 'use dmy dates', 'disputed', 'citation style',
        'citation needed','cn','failed verification','page needed','refimprove section',
        'unreferenced section','logical connectives sidebar','portal','refbegin','refend',
        'types of programming languages','programming languages','computer language',
        'computer science','sister bar','authority control','user-generated source'}


def native(text):
    code=mw.parse(text)
    for t in reversed(list(code.filter_templates())):
        n=str(t.name).strip().lower()
        repl=None
        if n=='!':
            repl='&#124;'
        elif n in {'emdash','endash','spaced ndash'}:
            repl={'emdash':'—','endash':'–','spaced ndash':' – '}[n]
        elif n.startswith('cite ') or n=='citation':
            repl=citation(t)
            # Restore source author/title topic links before central target mapping.
            for suffix in ['']+[str(i) for i in range(1,10)]:
                target=param(t,'author-link'+suffix) or param(t,'author'+suffix+'-link')
                author=param(t,'author'+suffix)
                last,first=param(t,'last'+suffix),param(t,'first'+suffix)
                if last or first:
                    author=', '.join(x for x in [last,first] if x)
                if author.endswith('.'):
                    repl=repl.replace(author+'. ',author+' ',1)
                if target and author and author in repl:
                    repl=repl.replace(author,'[['+target+'|'+author+']]',1)
            target=param(t,'title-link')
            title=param(t,'title')
            if target and title and not param(t,'url'):
                repl=repl.replace("''"+title+"''", "[["+target+"|''"+title+"'']]",1)
            if repl.endswith('..'):
                repl=repl[:-1]
        elif n=='sfn':
            vals=[str(p.value).strip() for p in t.params if str(p.name).strip().isdigit()]
            pages=param(t,'p') or param(t,'pp')
            repl='<ref>'+'; '.join(vals[:-1])+' ('+vals[-1]+')'+(', p. '+pages if pages else '')+'.</ref>'
        elif n=='isbn':
            repl='<nowiki>ISBN '+param(t,'1')+'</nowiki>'
        elif n=='webarchive':
            repl='['+param(t,'url')+" tahiry tamin' ny "+param(t,'date')+']'
        elif n=='anchor':
            repl='<span id="'+param(t,'1').replace(' ','_')+'"></span>'
        elif n in OMIT or n.startswith('defaultsort:'):
            repl=''
        elif n in {'main','see also','details'}:
            vals=[str(p.value).strip() for p in t.params if str(p.name).strip().isdigit()]
            labels={
                'Data type':'karazana angona',
                'Type system':'rafitra mamaritra ny karazana angona',
                'Type safety':"fiarovana amin' ny fampiasana karazana angona",
                'Primitive data type':'karazana angona fototra',
                'Syntax (programming languages)':'fitsipi-panorenan' + "' ny fiteny fampandaharana",
                'Semantics (programming languages)':"hevitra omen' ny fiteny fampandaharana ny kaody",
                'History of programming languages':"tantaran' ny fiteny fampandaharana",
                'Concurrent computing':'fikirakirana mifanindran-dalana',
                'Exception handling':'fikarakarana tranga maningana',
                'Programming language design and implementation':"famolavolana sy fanatanterahana fiteny fampandaharana",
                'Programming language implementation':"fanatanterahana fiteny fampandaharana",
                'Programming language specification':"famaritana ny fiteny fampandaharana",
                'Categorical list of programming languages':"lisitra voasokajin' ny fiteny fampandaharana",
            }
            unknown=set(vals)-set(labels)
            if unknown:
                raise RuntimeError('Missing translated template labels: '+str(unknown))
            repl='Jereo koa: '+', '.join('[['+v+'|'+labels[v]+']]' for v in vals)+'.'
        elif n=='reflist':
            repl='<references />'
        if repl is not None:
            try:
                code.replace(t,repl)
            except ValueError:
                pass
    return str(code)


def links(text,mapping):
    code=mw.parse(text)
    decisions=[]
    verified={v['mg'] for v in mapping.values() if v.get('mg')}
    verified.update({'Kajimirindra','Solosaina'})
    for link in list(code.filter_wikilinks()):
        target=str(link.title).strip()
        if target.startswith(('File:','Sary:',':Sokajy:','#')):
            continue
        label=str(link.text) if link.text is not None else target
        base,_,anchor=target.partition('#')
        item=mapping.get(base.replace('_',' '),{})
        mg=base if base in verified else item.get('mg')
        repl=('[['+mg+'|'+label+']]' if label!=mg else '[['+mg+']]') if mg else label
        try:
            code.replace(link,repl)
            decisions.append({'source_target':target,'label':label,'destination':mg,
                              'handling':'verified local topic; unverified cross-page anchor omitted' if mg and anchor else
                                         'verified local topic' if mg else 'plain text; no verified same-topic Malagasy target'})
        except ValueError:
            pass
    return str(code),decisions


def main():
    plan=read_json(JOB/'section-plan.json')
    mapping=read_json(JOB/'link-map.json')
    fragments=[];notes=[];vocab=[];decisions=[]
    for p in plan:
        d=Path(p['directory'])
        for n in ('section.wiki','notes.wiki','vocabulary.json'):
            if not (d/n).is_file():
                raise RuntimeError('Missing section artifact: '+str(d/n))
        s=(d/'section.wiki').read_text(encoding='utf-8')
        if not s.strip():
            raise RuntimeError('Empty section: '+p['id'])
        text,ds=links(native(s),mapping)
        fragments.append(text.strip())
        decisions.extend(dict(section=p['id'],**x) for x in ds)
        notes.append('# '+p['id']+'\n\n'+(d/'notes.wiki').read_text(encoding='utf-8'))
        records=read_json(d/'vocabulary.json')
        if isinstance(records,dict):
            records=records.get('entries',records.get('terms',[]))
        for r in records:
            r['section_id']=p['id']
            vocab.append(r)
        p['status']='integrated_pending_review'
    draft='\n\n'.join(fragments)+'\n'
    if mw.parse(draft).filter_templates():
        raise RuntimeError('Unadapted templates: '+str([str(t.name) for t in mw.parse(draft).filter_templates()]))
    (JOB/'draft.wiki').write_text(draft,encoding='utf-8')
    write_json(JOB/'link-decisions.json',decisions)
    write_json(JOB/'worker-vocabulary.json',vocab)
    write_json(JOB/'integrated-section-plan.json',plan)
    (JOB/'section-handoffs.md').write_text('\n\n'.join(notes),encoding='utf-8')
    (JOB/'draft-readable.txt').write_text('\n'.join('\n'.join(textwrap.wrap(
         line,140,replace_whitespace=False,drop_whitespace=False,break_long_words=False,
         break_on_hyphens=False)) for line in draft.splitlines())+'\n',encoding='utf-8')
    print('Integrated',len(plan),'sections;',len(decisions),'link decisions;',len(vocab),'worker term notes')


if __name__=='__main__':
    main()
