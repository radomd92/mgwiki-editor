"""Serialize remaining sense checks; reuse raw evidence, never edit remote pages."""
import argparse
from pathlib import Path

from mgwiki_editor.core import GuardError, lookup, now, read_json, write_json
from programming_plan import JOB

EXTRA = '''comment|fanamarihana
implementation|fanatanterahana
execution|fanatanterahana
process|fizotra
virtual machine|milina
hardware|fitaovana
computer language|fiteny
input format|endrika
subset|sokajy
formula|raikipohy
grammar|fitsipika
formal semantics|hevitra
parsing|famakafakana
reduction|famadihana
compilation|fandikana
formalism|fomba
compile time|fandikana
static code analysis|famakafakana
type coercion|fanovana
type error|hadisoana
character|tarehintsoratra
user-defined type|karazana
ordinal data type|karazana
information hiding|fanafenana
data abstraction|fanafenana
data structure|fandaminana
implicit typing|famaritana
instruction|baiko
subprogram|zana-pandaharana
processor|ventim-pikirakirana
interpreted language|fiteny
exception handler|fikarakarana
index|tondro
return value|sanda
natural-language programming|fampandaharana
formal grammar|fitsipika
interpretation|fandikana
intermediate language|fiteny
executable|fandaharana
production code|kaody
debugging|fanitsiana
memory|fitadidiana
software|rindrankajy
intellectual property|fananana
open science|siansa
replication|famerenana
average|sala
command-line interface|fifandraisana
interactive session|fifandraisana
real-time|fotoana
embedded software|rindrankajy
standard|fenitra
documentation|tahirin-kevitra
computer programming|fampandaharana
computer science|kajimirindra
domain-specific modeling|modely
educational programming language|fampianarana
esoteric programming language|fanandramana
extensible programming|fanitarana
invariant|toetra
language-oriented programming|fampandaharana
literate programming|fanazavana
modeling language|modely
programming language theory|teôria
scientific programming language|siansa
software engineering|injenieria'''

ROOT_CORRECTIONS = ['firafitra','fiantsoana','fitoviana','fifanarahana',
                    'fifandonana','fahaleovantena','fandinihana','fameno','sampana']


def plan():
    work=[]
    for i,line in enumerate(EXTRA.splitlines(),1):
        en,mg=line.split('|')
        for lang,word in [('en',en),('mg',mg)]:
            work.append({'edition':lang,'word':word,
                         'output':f'evidence/lookup-supp-{i:03}-{lang}.json'})
    for i,word in enumerate(ROOT_CORRECTIONS,1):
        work.append({'edition':'mg','word':word,
                     'output':f'evidence/lookup-root-{i:02}.json'})
    write_json(JOB/'supplement-lookup-plan.json',work)
    print('Pinned supplemental plan:',len(work),'items before exact-query cache reuse')


def run():
    cached={}
    for t in read_json(JOB/'term-inventory.json'):
        for lang,word in [('en',t['source_term']),('mg',t['candidate_lookup'])]:
            f=JOB/'evidence'/f"lookup-{lang}-{t['id']}.json"
            if f.exists():
                cached[(lang,word)]=f
    for f in Path('runs').rglob('lookup*.json'):
        try:
            d=read_json(f)
        except (OSError,ValueError):
            continue
        if isinstance(d,dict) and d.get('edition') in ['en','mg'] and d.get('word'):
            key=(d['edition'],d['word'])
            if key not in cached or d.get('status')=='found':
                cached[key]=f
    for item in read_json(JOB/'supplement-lookup-plan.json'):
        lang,word=item['edition'],item['word'];f=JOB/item['output']
        if f.exists():
            cached[(lang,word)]=f
            continue
        if (lang,word) in cached:
            f.write_bytes(cached[(lang,word)].read_bytes())
        else:
            try:
                data=lookup(lang,word)
            except Exception as exc:
                message=str(exc)
                if any(x in message.lower() for x in ['cooldown','deferred','circuit','overload','ratelimit']):
                    write_json(JOB/'evidence/dictionary-supplement-stop.json',
                        {'at':now(),'status':'deferred','item':item,'error_type':type(exc).__name__,'error':message})
                    raise
                if not isinstance(exc,GuardError):
                    raise
                data={'edition':lang,'word':word,'status':'failed','retrieved_at':now(),'error':message}
            write_json(f,data)
        cached[(lang,word)]=f
    write_json(JOB/'supplement-completion.json',{'status':'complete','at':now()})
    print('Supplemental dictionary checks complete; sense review remains coordinator-only.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['plan','run'])
    args=p.parse_args();(plan if args.action=='plan' else run)()
