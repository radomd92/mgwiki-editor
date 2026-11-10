"""Coordinator-only exact integration and narrow-edit integrity review."""
import difflib
from pathlib import Path
import mwparserfromhell as mw
from mgwiki_editor.core import GATES, read_json, write_json, digest, now, lint_wikitext
from iliad_troasy_plan import JOB, QUOTE, revise_name

def protected_signature(text):
 code=mw.parse(text)
 return {
  'ref_tags':[str(t) for t in code.filter_tags() if str(t.tag).lower() in {'ref','references'}],
  'nowiki':[str(t) for t in code.filter_tags() if str(t.tag).lower()=='nowiki'],
  'italics':[str(t) for t in code.filter_tags() if str(t.tag).lower()=='i'],
  'targets':[str(l.title) for l in code.filter_wikilinks()],
  'external_urls':[str(l.url) for l in code.filter_external_links()],
  'headings':[str(h) for h in code.filter_headings()],
  'quotations':QUOTE.findall(text),
 }

def main():
 plan=read_json(JOB/'section-plan.json');state=read_json(JOB/'job.json');base=state['sandbox']['text'];parts=[];worker_notes=[];vocab=[];counts=0;evidence=[]
 for r in plan:
  d=JOB/'sections'/r['id']
  for name in ('section.wiki','notes.wiki','vocabulary.json'):
   if not (d/name).is_file():raise RuntimeError('Missing section output: '+str(d/name))
  actual=(d/'section.wiki').read_bytes();candidate=(d/'candidate.wiki').read_bytes();source=(d/'source.wiki').read_bytes()
  if actual!=candidate:
   raise RuntimeError('Targeted section follow-up needed; output differs from strict name-only candidate: '+r['id'])
  assert protected_signature(source.decode('utf-8'))==protected_signature(actual.decode('utf-8')),r['id']
  parts.append(actual);counts+=r['replacement_count']
  r['status']='accepted_by_coordinator' if r['replacement_count'] else 'unchanged_reused_and_checked'
  r['reviewed_at']=now();r['section_sha256']=digest(actual)
  if 'start_byte' in r:r['start_char']=r.pop('start_byte');r['end_char']=r.pop('end_byte')
  worker_notes.append('== '+r['id']+' ==\n'+(d/'notes.wiki').read_text(encoding='utf-8'))
  for name in ('source.wiki','candidate.wiki','candidate-diff.json','section.wiki','notes.wiki','vocabulary.json'):
   evidence.append(str((d/name).relative_to(JOB)))
  for v in read_json(d/'vocabulary.json'):
   v=dict(v);v['section_id']=r['id'];vocab.append(v)
 draft=b''.join(parts).decode('utf-8')
 expected,changes=revise_name(base)
 assert draft==expected
 assert counts==sum(x['count'] for x in changes)==58
 assert not draft.endswith('\n') and not base.endswith('\n')
 assert protected_signature(base)==protected_signature(draft)
 assert not lint_wikitext(draft)
 (JOB/'draft.wiki').write_bytes(draft.encode('utf-8'))
 write_json(JOB/'section-plan.json',plan)
 (JOB/'section-handoff-notes.wiki').write_text('\n\n'.join(worker_notes),encoding='utf-8')
 write_json(JOB/'section-vocabulary-evidence.json',vocab)
 review={'reviewed_at':now(),'city_name_replacements':counts,'changed_sections':sum(r['replacement_count']>0 for r in plan),'unchanged_sections':sum(r['replacement_count']==0 for r in plan),'protected_signatures_equal':True,'baseline_sha256':digest(base.encode('utf-8')),'draft_sha256':digest(draft.encode('utf-8')),'diff_only_user_requested_city_names':True,'final_newline_preserved_absent':True,'mainspace_missing':state['existing']['revision_id'] is None}
 write_json(JOB/'name-change-audit.json',review)
 (JOB/'naming-changes.diff').write_text(''.join(difflib.unified_diff(base.splitlines(True),draft.splitlines(True),fromfile='pinned sandbox1153305',tofile='Troasy proposal')),encoding='utf-8')
 files=evidence+['user-request.wiki','shared-context.wiki','shared-references.wiki','section-plan.json','section-handoff-notes.wiki','section-vocabulary-evidence.json','name-change-audit.json','naming-changes.diff','candidate-correction.json','prior-vocabulary.json','prior-review.json','prior-receipt.json','prior-proposal.json','link-map.json','naming-evidence/mg-verify-000.json','naming-evidence/mg-verify-045.json','country-names.json','source.wiki','existing.wiki','sandbox.wiki']
 write_json(JOB/'vocabulary.json',[{'source_term':'Troy / Trôia / Troie','source_language':'en','domain':'ancient city name; user-requested Malagasy spelling','source_sense':'The ancient city Troy in the Iliad, not a film, book, quoted title or current Wikipedia page title.','english_definition':'The ancient city besieged in the Trojan War and named in the Iliad.','definition_origin':'editorial_simple_english','malagasy_definition':"Ilay tanàna fahiny natao fahirano tamin’ ny Adin’ i Troasy sady toerana resahina ao amin’ ny Iliasy.",'chosen_expression':'Troasy','evidence_files':sorted(set(files)),'alternatives_rejected':['Troy, Troie, Trôia as visible city labels in new Malagasy prose; retained where required as original quotations/titles or exact link targets'],'status':'descriptive','reason':'Explicit user-provided proper-name preference. Meaning and topic identity unambiguous from the unchanged pinned source and existing Trôia link mapping. Not claimed to be dictionary-verified, an official translation, a page rename or community consensus. No dictionary lookup or country-name refresh is needed for this preference; country names and all other terminology are unchanged.'}])
 with (JOB/'notes.wiki').open('a',encoding='utf-8') as f:f.write("""
== Fanakambanana sy fanamarinana manerana ny lahatsoratra ==
Fizarana 18 misy fanovana no nojerena tsirairay tamin’ ny mgwiki-section; fizarana sivy tsy misy fanovana, anisan’ ny appendices, no naverina byte-for-byte avy amin’ ny sandbox nekena. Tsy namokatra fandikana vaovao ny mpandrindra: natambatra araka ny filaharana ireo fragments nekena ary nohamarinina tamin’ ny base manontolo. Feno ny plan: tsy misy fizarana tsy hita na voasakana navela hiala.
Fanoloana anaran-tanàna 58 ihany no ao amin’ ny naming-changes.diff. Nahita ilay candidate iray tsy nahita mari-teny nanodidina wikilink ny mpiasa lead, ka notazoniny ny quoted gloss tany am-boalohany; neken’ ny mpandrindra io fanitsiana marina io ary nahitsy ny candidate helper mba hiaro quotes manerana ny AST nodes, fa tsy nalefahana ny integrity signature. Voatahiry ao amin’ ny candidate-correction.json ny porofo; tsy naverina noforonina ilay lead. Troasy no ao amin’ ny prose sy captions malagasy tsy voaaro; tsy noforonina ny ethnonyme Troasiana, ka voatahiry ny Troiana. Mbola Trôia ny kendren-drohy efa voamarina fa Troasy ny label. Tsy nisy fanovana mainspace na page move. Ireo Troy ao amin’ ny lohatenim-boky/sarimihetsika sy quotations na metadata dia voatahiry, anisan’ ny Troy, Helen of Troy, The Women of Troy sy ireo glosses voatonona. Tsy filazana fa efa fanoratana ofisialy ny Troasy: safidin’ ny mpampiasa.
Ny ref/references tags manontolo, citation metadata, nowiki identifiers, italics/original titles, quotations, URL rehetra, wikilink targets/filaharany ary headings dia mitovy byte-for-byte amin’ ny base araka ny protected signatures. Ny sary 12 sy ny filenames/options rehetra dia voatahiry, captions ihany no ahitana anaran-tanàna novana. Tsy nisy reference vaovao, claim vaovao, fanesorana votoaty, fanovana chronology, figure, name order, acronym, medical definition na source attribution. Tsy nisy rohy ivelany nosokafana na resource nalaina; mitovy ny bibliographic limitations sy fanapahan-kevitra efa voarakitra ao amin’ ny prior proposal sy lexical memo.
Sokajy roa inert teo aloha, Boky sy Angano grika, dia mitovy tanteraka amin’ ny filaharana sy bytes teo aloha; tsy nisy sokajy vaovao na categorization/interwiki side effects niniana nampiana. Ny country-names.json sy porofo momba ny targets dia kopia pinned, tsy refresh lavitra. Tsy nisy firenena na anarana hafa novana.
Meaning/coverage/neutrality/existing_preserved: fanovana anaran’ ilay tanàna iray ihany, tahaka ny nangatahan’ ny mpampiasa, amin’ ny lahatsoratra sandbox efa voavaky sy nekena; voatahiry ny contributions/references rehetra. Fluency/terminology: mitovy ny fehezanteny sy Malagasy elision spacing, Troasy ihany no city-name token vaovao, misy famaritana anglisy tsotra sy malagasy ary user-preference evidence marina. Links/templates/citations: protected signatures unchanged, refs sy groups mbola manana renderers, tsy misy templates nampiana. Wikitext-only: raw naming diff sy fragments ary assembled structure nojerena; offline validate tsy misy error. Tsy fanamarinana nataon’ olombelona ireo attestations ireo. Tsy maintsy jerena offline ny preview sy hash exact aorian’ ny prepare alohan’ ny publish.
Tazonina tsy misy LF fanampiny ny faran’ ny draft, mitovy amin’ ny source sandbox, mba tsy hisy serialization mismatch toy ny tamin’ ny asa teo aloha. Tsy nalefahana ny publication/revision/account/hash guards.
""")
 write_json(JOB/'review.json',dict.fromkeys(GATES,True))
 print('Integrated',len(plan),'sections;',counts,'city-name replacements; all protected content exactly unchanged')

if __name__=='__main__':main()
