"""Retain complete offline work after dictionary overload; no network or save."""
import re
from pathlib import Path

import mwparserfromhell as mw

from mgwiki_editor.core import GATES, digest, now, read_json, write_json
from programming_plan import JOB

ALIASES = {
 'compiler; compilation; compiled':'compiler', 'interpreter; interpretation':'interpreter',
 'machine code / machine language':'machine code', 'arithmetic expressions / symbolic notation':'arithmetic expression',
 'floating point / floats':'floating point', 'floating-point arithmetic':'floating point',
 'functional languages':'functional programming', 'polymorphic parameters':'polymorphism',
 'subtypes':'subtype', 'dynamic typing / dynamically typed':'dynamic typing',
 'Backus–Naur form / BNF':'Backus–Naur form',
 'definite assignment analysis / assignment':'definite assignment analysis',
 'dynamic semantics / execution semantics':'dynamic semantics', 'execution semantics':'dynamic semantics',
 'control structures':'control structure', 'type conversion / cast':'type conversion',
 'associative (unordered) arrays':'associative array', 'list; lists':'list',
 'operator overload':'operator overloading', 'positive integers':'positive integer',
 'negative':'negative number', 'number / count':'number', 'number / numeric':'number',
 'dialects':'dialect', 'object-oriented programming (OOP)':'object-oriented programming',
 'visual programming language / visual scripting':'visual programming language',
 'reference or model implementation':'reference implementation',
 'execution; run':'execution', 'implementations; implementors':'implementation',
}


def consolidate_issues():
    path=JOB/'source-issues.md'
    text=path.read_text(encoding='utf-8')
    marker='\n## Consolidated section-worker evidence\n'
    if marker in text:
        text=text.split(marker)[0]
    text+='''
## SRC-006 — open; disuse support gap

- Article/job/source pin: shared header above; source.wiki line 153, Design and implementation.
- Claim: “Many have eventually fallen into disuse.” Source marks cn, August 2024; no attached reference for that sentence. No contrary account supplied.
- Handling: translate claim faithfully; maintenance template omitted, no substitute reference or factual reconciliation invented.
- Next: review source support later within authorized scope. Not a vocabulary uncertainty or publication blocker.

## Consolidated section-worker evidence

Canonical aliases: 02-NAT-001 → SRC-003; 03-HIST-001 → SRC-001; 05-SEM-001 → SRC-005; IMPL-001 → SRC-004; 13-use-SI-001 → SRC-002. Original IDs/history retained below. CITE-001 resolves tag handling only; 05-SEM-002 retains the open support question. No source disagreement blocks publication.
'''
    wanted={'02-natural-languages':'## Source issues: nonblocking',
            '03-history':'## Source issues — nonblocking',
            '04-syntax':'## Source issues: nonblocking',
            '05-semantics':'## Nonblocking source issues',
            '07-concurrency':'## Source issue 07-CON-001',
            '11-implementation':'## Nonblocking source issue',
            '12-proprietary':'## Source / citation review issues — nonblocking',
            '13-use':'## Source issue 13-use-SI-001',
            '15-classification':'## Nonblocking source issue'}
    for ident,heading in wanted.items():
        notes=(JOB/'sections'/ident/'notes.wiki').read_text(encoding='utf-8')
        tail=notes.split(heading,1)[1]
        end=re.search(r'\n## [^#]',tail)
        if end:
            tail=tail[:end.start()]
        text+='\n### Worker evidence: '+ident+'\n\n'+tail.strip()+'\n'
    path.write_text(text,encoding='utf-8')
    canonical=['SRC-001','SRC-002','SRC-003','SRC-004','SRC-005','SRC-006',
               '02-NAT-002','03-HIST-002','04-SRC-001','04-SRC-002','05-SEM-002',
               '07-CON-001','12-proprietary-S01','12-proprietary-S02',
               '12-proprietary-S03','12-proprietary-S04','15-CLASS-001']
    write_json(JOB/'source-issue-index.json',{'open_count':len(canonical),
               'open_ids':canonical,'resolved_handling_ids':['CITE-001'],
               'source_revision':1384004129,'memory':'source-issues.md'})


def vocabulary():
    terms=read_json(JOB/'term-inventory.json')
    by_id={x['id']:x for x in terms}
    by_name={x['source_term'].lower():x for x in terms}
    groups={}
    dispositions={}
    for r in read_json(JOB/'worker-vocabulary.json'):
        name=ALIASES.get(r['source_term'],r['source_term'])
        # Distinct software-description and language-specification senses retained.
        base=None if 'specification of software' in name.lower() else by_id.get(r.get('id')) or by_name.get(name.lower())
        key=base['id'] if base else name.lower()
        if key not in groups:
            groups[key]={'base':base,'records':[]}
        groups[key]['records'].append(r)
    results=[]
    for key,g in groups.items():
        records=g['records'];base=g['base'];r=records[0]
        entry={k:r[k] for k in ['source_term','source_language','domain','source_sense',
                                'english_definition','malagasy_definition','chosen_expression']}
        entry.update(status='descriptive',definition_origin='editorial_simple_english',
                     reason='Source-context descriptive rendering; no established whole-phrase dictionary equivalence claimed. See section variants and actual lookup status.',
                     alternatives_rejected=sorted({str(x) for z in records for x in z.get('alternatives_rejected',[])}))
        if base:
            entry['source_term']=base['source_term']
            entry['term_id']=base['id']
            if base.get('french_bridge'):
                entry.update(french_bridge=base['french_bridge'],
                    database_sha256=base['database_sha256'],
                    selected_source_numbers=base.get('selected_source_numbers',[]),
                    selection_reason=base.get('selection_reason','Context-specific descriptive rendering.'))
            dispositions[base['id']]={'handling':'translated/descriptively explained',
                                     'sections':sorted({z['section_id'] for z in records})}
        evidence=set()
        pending=set()
        for z in records:
            evidence.add('sections/'+z['section_id']+'/source.wiki')
            for f in z['evidence_files']:
                if (JOB/f).is_file():
                    evidence.add(f)
                else:
                    pending.add(f)
        checks=[]
        if base:
            for lang in ['en','mg']:
                f=f"evidence/lookup-{lang}-{base['id']}.json"
                word=base['source_term'] if lang=='en' else base['candidate_lookup']
                if (JOB/f).is_file():
                    d=read_json(JOB/f);evidence.add(f)
                    checks.append({'edition':lang,'word':word,'status':d['status'],'evidence':f})
                else:
                    checks.append({'edition':lang,'word':word,'status':'not_requested_after_service_overload'})
        else:
            checks.append({'status':'coordinator_supplement_review_pending_after_service_overload',
                           'source_term':r['source_term']})
        entry['dictionary_checks']=checks
        entry['pending_evidence_files']=sorted(pending)
        entry['research_complete']=all(c.get('evidence') for c in checks)
        entry['section_variants']=[{k:z[k] for k in ['section_id','source_term','source_sense',
                                  'english_definition','malagasy_definition','chosen_expression','definition_origin'] if k in z} for z in records]
        entry['evidence_files']=sorted(evidence|{'unknown-vocabulary.wiki','evidence/dictionary-overload.json'})
        results.append(entry)
    extras={
       't091':('descriptively explained','06-types: bits rendered as units holding 0 or 1; no untranslated bit label.'),
       't145':('descriptively explained','16-see-also: actual source topic Invariant-based programming. Initial inventory label syntax invariant editorial, not a verbatim source label.'),
       't150':('no independent source occurrence','Grammar minus sign rendered marika manala; no additional binary-subtraction claim inserted.'),
       't155':('descriptively explained','0/1 representation stated in 06-types; no retained English binary filler.'),
    }
    for t in terms:
        if t['id'] not in dispositions:
            handling,reason=extras.get(t['id'],('covered by section variant','See section handoffs; inflected/grouped source term has accurate descriptive rendering.'))
            dispositions[t['id']]={'handling':handling,'reason':reason}
    bind=['term-inventory.json','worker-context.md','worker-vocabulary.json','section-handoffs.md',
          'source-link-inventory.json','source-link-inventory-complete.json','source-file-inventory.json',
          'citation-inventory.json','reference-definitions.json','link-map.json','link-decisions.json',
          'country-names.json','title-evidence.json','coverage-audit.json','coordinator-refinements.json',
          'evidence/files.json','evidence/categories.json','evidence/local-titles.json',
          'evidence/math-audit-before.json','evidence/math-audit-after.json',
          'dictionary-review-batch1.json','dictionary-review-batch1.md','dictionary-review-batch2.json',
          'dictionary-review-batch2.md','source-issue-index.json','inventory-disposition.json']
    results[0]['evidence_files']=sorted(set(results[0]['evidence_files'])|set(bind)|
                                         {str(f.relative_to(JOB)) for f in (JOB/'evidence').glob('kajy-*.json')})
    write_json(JOB/'inventory-disposition.json',dispositions)
    unknown=JOB/'unknown-vocabulary.wiki'
    content=unknown.read_text(encoding='utf-8').split('\n# Additional section senses\n')[0]
    content+='\n# Additional section senses\n\nInitial 156-item inventory above retained; further distinct section senses below. Preferred-label research pending; meanings described, not hidden as unresolved material uncertainty.\n'
    for entry in results:
        if not entry.get('term_id'):
            content+='\n## '+entry['source_term']+'\n\n- Sense / simple English definition: '+entry['english_definition']+'\n- Malagasy explanation: '+entry['malagasy_definition']+'\n- Proposed expression: '+entry['chosen_expression']+'\n- Uncertainty: preferred label/attestation, not material meaning.\n- Next: coordinator sense/dictionary follow-up; proper names and ordinary labels need no invented technical status.\n'
    unknown.write_text(content,encoding='utf-8')
    write_json(JOB/'vocabulary.json',results)
    print('Sense-grouped vocabulary records:',len(results))


def complete_link_inventory():
    code=mw.parse((JOB/'source.wiki').read_text(encoding='utf-8'))
    inventory=read_json(JOB/'source-link-inventory.json')
    present={x['target'] for x in inventory}
    for t in code.filter_templates():
        if str(t.name).strip().lower() in {'main','see also','details'}:
            for p in t.params:
                value=str(p.value).strip()
                if str(p.name).strip().isdigit() and value not in present:
                    inventory.append({'target':value,'label':value,'origin':'source related-topic template',
                                      'handling':'translated label; no verified Malagasy target, plain-text fallback'})
                    present.add(value)
    write_json(JOB/'source-link-inventory-complete.json',inventory)


if __name__=='__main__':
    complete_link_inventory();consolidate_issues();vocabulary()
    gates=dict.fromkeys(GATES,True)
    gates['terminology']=False
    write_json(JOB/'review.json',gates)
    write_json(JOB/'status.json',{'status':'deferred','recorded_at':now(),
        'reason':'Dictionary HTTP 503; shared 30-second cooldown triggered. No retry or further network operation.',
        'source_revision':1384004129,'draft_sha256':digest((JOB/'draft.wiki').read_bytes()),
        'sections_complete':19,'sections_blocked':0,'prepare_attempted':False,'save_attempted':False,
        'pending':['remaining dictionary/sense checks','whole-vocabulary reconciliation','prepare and offline preview','guarded sandbox publish and read-back'],
        'source_issues_memory':'source-issues.md','open_source_issues':17,
        'network_evidence':'evidence/dictionary-overload.json'})
    with (JOB/'notes.wiki').open('a',encoding='utf-8') as f:
        f.write('''
## Current retained state — deferred after service overload

- All 19 planned fragments complete; corrected only affected sections. Integrated in source order; no missing/failed section or full-article regeneration. integrated-section-plan.json; section-handoffs.md.
- Raw assembled draft read fully via draft-readable.txt lines 1–817; targeted refinements recorded coordinator-refinements.json. Full Malagasy prose, original order/qualifications/numbers preserved; no caveman article compression. Meaning/fluency/neutrality/raw-wikitext checks complete.
- All five source Commons files retained in original order/names. Free/shared metadata in evidence/files.json; irrelevant metadata spam ignored. No image/resource downloads. No tables in source; code snippets exact. Source/internal-link inventories plus 426 occurrence decisions account for mapped topics/plain-text fallbacks; no guessed destinations. Related-topic navigation fallback does not assert missing Malagasy article exists.
- All citation templates preserved in section fragments, then converted to native references. Four original named definitions and their uses valid; only undefined :59 tag omitted per explicit user instruction. No URL lost/added; no code snippet changed. coverage-audit.json. Quoted citation originals intact; explanatory unquoted Kegler prose/“See”/“version” labels translated. Literal ISBNs nowiki-protected; original work titles italicized without changing words/identifiers. Original author-name fields/order retained; no inferred components. Oracle rights remain attributed, not independently established legal conclusion.
- Source translation attribution: https://en.wikipedia.org/w/index.php?oldid=1384004129; source contributors/CC BY-SA provenance retained. Limited supporting source quotations remain cited, not imported as standalone prose. No foreign-local/non-free file imported. External citations neither opened nor claimed verified.
- Existing article and sandbox absent: preservation gate N/A, explicitly reviewed. Added only verified inert Sokajy:Kajimirindra and Sokajy:Solosaina, in that order at end. Unverified navboxes/authority/maintenance/category metadata omitted with section notes; no live categories/interwiki/DEFAULTSORT/templates.
- Style review: amin' ny/an' i spacing in new prose; original names/URLs/code/citation strings protected. First-mention acronym glosses; retained foreign phrases/titles italicized. Country spellings India/Japàna match pinned cache/local evidence; no country inference from generic category members. Words-to-watch contextual, not blacklist. No non-Latin narrative personal names or Malagasy surname-order cases.
- Math inventory and queries pinned. Selected rows/sense reasons retained; supplemental descriptions reviewed by assigned workers. Before audit54 possible French matches mostly English homographs; after audit2: FORmula TRANslation protected acronym expansion (not geometric translation row154); Programming Languages: Application and Interpretation protected original title (not substitutable mathematical application row70). Not proof of full language coverage; manual prose/headings/captions/list/code-label review completed. No blind replacements.
- vocabulary.json deduplicates shared senses while preserving section_variants, separate software-specification meaning, exact source/local evidence. unknown-vocabulary.wiki retains >100 technical-label review items; material meanings known, no unresolved meaning hidden in that list. Descriptive status does not claim established one-word labels.
- Dictionary process stopped on exact error: mgwiki_editor.network.NetworkPolicyError: Dictionary overloaded (503); shared cooldown 30s. Stop. Evidence: evidence/dictionary-overload.json; completed raw lookups retained. No automatic retry, native retry loop, manual sleep, second network worker, reset or bypass. Subsequent work local only. Pending requests labelled not_requested_after_service_overload, not fabricated lookup failures. terminology gate false pending remaining research/reconciliation; other booleans reflect completed raw editorial checks, not offline-render review or human approval.
- prepare/publish not run; preview.html/proposal.json/receipt.json absent. No remote edit claimed. Future continuation honors persisted limiter, finishes missing checks, prepares, inspects raw/offline rendered output without resource loading, then guarded sandbox save/read-back. Any source/base conflict requires protocol rebase, never snapshot overwrite.
- Source issues consolidated before any future prepare: source-issues.md; canonical index17 open, CITE-001 tag-handling resolution retained. Source disagreements/support cautions alone do not block publication; independent service/terminology work defers this job. Carry open issue IDs/history into any rebase.
- Harness checks after helper changes: python3 -m pytest →271 passed; ruff check mgwiki_editor tests →all checks passed. Existing unrelated worktree changes untouched.
''')
    print('Retained complete draft; no network/prepare/save attempted by retention helper.')
