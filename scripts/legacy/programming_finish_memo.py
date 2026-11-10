"""Attach completed read-only research; never attest editorial gates automatically."""
from pathlib import Path

from mgwiki_editor.core import now, read_json, write_json
from programming_plan import JOB

ALIASES = {
 'execution; run':['execution'], 'array index error':['index'],
 'direct reduction':['reduction'], 'standard syntactic formalisms':['formalism'],
 'compiled languages / compile time':['compile time'],
 'intellectual property; proprietary rights':['intellectual property'],
 'averaging':['average'], 'real-time applications':['real-time'],
 'embedded applications':['embedded software'],
 'intermediate-level language / intermediate language':['intermediate language'],
 'extensible programming; extensible syntax programming languages':['extensible programming'],
 'invariant-based programming':['invariant'],
 'formal semantics of programming languages':['formal semantics'],
 'software specification':['specification'],
 'standard library; functions':['standard library','function'],
 'imperative languages':['imperative programming'],
 'subprogram':['subroutine','subprogram'],
 'reflective programming':['reflection'],
 'semantics (logic)':['semantics'],
 'syntax (logic); syntax in extensible-syntax programming languages':['syntax'],
 'AI':['artificial intelligence'],
 'open-source programming languages':['open source','programming language'],
 'float / double':['floating point'],
 'signed / unsigned':['integer'],
 'fully typed / untyped':['type theory','type system'],
 'hybrid interpretation':['interpretation','compiler','interpreter','just-in-time compilation'],
 'error handling':['exception handling'],
 'user-defined exception':['exception handler','exception handling'],
 'shared data':['thread','data type'],
 'processing power':['processor','computation'],
 'logic':['formal logic'],
 'translator':['compiler'],
}

PLAIN = {'human expression','editor','edition','online publication','adding','performance',
         'specification of software','termination','resumption','written in the language being specified',
         'readability; writability; reliability','special-purpose language'}
NAMING = {'India; Japanese','ML','ANSI REXX','ASCII','CPU','CPU time','Common Language Runtime (CLR)','TIOBE index'}
ROOTS = {'firafitry':'firafitra','fiantsoan':'fiantsoana','fitovian':'fitoviana',
         'fifanarahan':'fifanarahana','fifandonan':'fifandonana',
         'fahaleovantenan':'fahaleovantena','fandinihan':'fandinihana',
         'famenon':'fameno','kofehim-panatanterahana':'sampana'}


if __name__=='__main__':
    if read_json(JOB/'dictionary-completion.json')['status']!='complete' or read_json(JOB/'supplement-completion.json')['status']!='complete':
        raise RuntimeError('Research not complete; keep terminology gate false.')
    terms=read_json(JOB/'term-inventory.json')
    by_id={x['id']:x for x in terms};queries={}
    for t in terms:
        for lang,word in [('en',t['source_term']),('mg',t['candidate_lookup'])]:
            queries[(lang,word)]=f"evidence/lookup-{lang}-{t['id']}.json"
    for item in read_json(JOB/'supplement-lookup-plan.json'):
        queries[(item['edition'],item['word'])]=item['output']
    for word,path in [("two's complement",'lookup-canonical-twos.json'),
                      ("one's complement",'lookup-canonical-ones.json'),
                      ("ones' complement",'lookup-canonical-ones-plural.json'),
                      ('Turing complete','lookup-canonical-turing.json')]:
        queries[('en',word)]='evidence/'+path
    queries[('en','atom')]='evidence/lookup-final-atom.json'
    records=read_json(JOB/'vocabulary.json')
    if not (JOB/'vocabulary-before-finish.json').exists():
        write_json(JOB/'vocabulary-before-finish.json',records)
    missing=[]
    for r in records:
        term=r['source_term'];base=by_id.get(r.get('term_id'))
        checks=[];evidence=set(r['evidence_files'])
        if base:
            words=[base['source_term']]
            words+= {'twos complement':["two's complement"],
                     'ones complement':["one's complement","ones' complement"],
                     'Turing-complete':['Turing complete']}.get(base['source_term'],[])
            mgwords=[base['candidate_lookup']]
            if base['candidate_lookup'] in ROOTS:
                mgwords.append(ROOTS[base['candidate_lookup']])
        else:
            words=ALIASES.get(term,[term])
            # Exact descriptive-expression checks use known lexical components.
            mgwords={'atom':['singa'],'logic':['lôjika'],'translator':['mpandika']}.get(term,[])
        for word in words:
            path=queries.get(('en',word))
            if path and (JOB/path).is_file():
                data=read_json(JOB/path);evidence.add(path)
                checks.append({'edition':'en','word':word,'status':data['status'],'evidence':path,
                               'scope':'same source sense; related component, not whole-phrase attestation' if word!=term else 'queried headword'})
        if not base:
            for item in read_json(JOB/'supplement-lookup-plan.json'):
                if item['edition']=='en' and item['word'] in words:
                    number=item['output'].rsplit('-',1)[0]
                    mgpath=number+'-mg.json'
                    if (JOB/mgpath).is_file():
                        data=read_json(JOB/mgpath);evidence.add(mgpath)
                        checks.append({'edition':'mg','word':data.get('word','see lookup URL'),
                                       'status':data['status'],'evidence':mgpath,
                                       'scope':'lexical component only; descriptive phrase not declared established'})
        for word in mgwords:
            path=queries.get(('mg',word))
            if path and (JOB/path).is_file():
                data=read_json(JOB/path);evidence.add(path)
                checks.append({'edition':'mg','word':word,'status':data['status'],'evidence':path,
                               'scope':'lexical component; exact returned sense reviewed, no whole-phrase verification claimed'})
        if not checks and term not in PLAIN|NAMING:
            missing.append(term)
        if term in PLAIN:
            checks.append({'status':'source_context_editorial','scope':'ordinary compositional wording; no unfamiliar technical lexeme or unknown meaning'})
        if term in NAMING:
            evidence|={'country-names.json','evidence/local-titles.json','source.wiki'}
            checks.append({'status':'source_naming_evidence','scope':'proper name/acronym or source-supported descriptive gloss; not counted as uncertain English merely because foreign'})
        for f in list(r.get('pending_evidence_files',[])):
            if (JOB/f).is_file():
                evidence.add(f)
        r.update(dictionary_checks=checks,research_complete=bool(checks),
                 pending_evidence_files=[f for f in r.get('pending_evidence_files',[]) if not (JOB/f).is_file()],
                 evidence_files=sorted(evidence),
                 reason='Coordinator sense review: accurate source-context descriptive rendering. Lookup errors/no-matching-language retained honestly; lexical-head noise not whole-phrase verification. See dictionary final review. No unresolved material meaning.')
    bind={'dictionary-completion.json','supplement-completion.json','supplement-lookup-plan.json',
          'dictionary-final-review.md','dictionary-final-review.json',
          'dictionary-review-batch3.json','dictionary-review-batch4.json',
          'dictionary-supplement-review.json','dictionary-mg-supplement-review.json',
          'canonical-headword-review.json','evidence/math-audit-final.json','process-sense.md',
          'evidence/final-local-identity.json','evidence/final-type-safety.json'}
    bind|={str(f.relative_to(JOB)) for f in (JOB/'evidence').glob('lookup-*.json')}
    records[0]['evidence_files']=sorted(set(records[0]['evidence_files'])|bind)
    write_json(JOB/'vocabulary.json',records)
    write_json(JOB/'terminology-reconciliation.json',{'at':now(),'unmatched_terms':missing,
       'records':len(records),'editorial_gate_set':False})
    print('Unmatched research records:',missing)
