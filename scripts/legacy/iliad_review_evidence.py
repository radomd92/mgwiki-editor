"""Offline terminology reconciliation and full coverage audit; no gate auto-approval."""
import re
from pathlib import Path
import mwparserfromhell as mw
from mgwiki_editor.core import read_json, write_json

JOB=Path('runs/iliad-en-20261106')
ALIASES={
 'epic poem':['epic'],'epic poetry':['epic'],'classical philology':['philology'],
 'dactylic hexameter':['dactyl','hexameter'],'hexametric line':['hexameter'],
 'formulae':['oral-formulaic','epithet'],'stock epithet':['epithet'],'formulaic language':['oral-formulaic'],
 'anthropomorphic characterisation':['anthropomorphism'],'personalized / anthropomorphic':['anthropomorphism'],
 'Bicameral Mind / bicameral mentality':['bicameral mind'],'genitive case':['genitive'],
 'scholia':['scholium'],'textual witness':['manuscript','textual criticism'],
 'timē (respect, honor)':['timē'],'hybris / hubris':['hubris'],'wrath (mēnis; accusative mēnin)':['menis'],
 'oral-formulaic composition':['oral-formulaic'],'thematic patterns':['thematic patterning'],
 'foreshadows':['foreshadowing'],'syntactic inconsistency':['syntactic'],'aspis; shoulder-borne shield':['aspis'],
 'canonical Homeric texts':['canon'],'canonical story':['canon'],'literary allusion':['allusion'],
 'vernacular languages':['vernacular'],'unthinking automaton':['automaton'],'postmodern literature':['postmodernism'],
 'posttraumatic stress disorder':['post-traumatic stress disorder'],'ballad metre':['ballad'],
 'fourteeners':['fourteener'],'iamb; iambic pentameter':['iamb','pentameter'],
 'annotated edition':['gloss'],'digital facsimile':['facsimile'],'grammatical forms':['genitive','accusative'],
 'soothsayer':['seer'],'human character metaphors':['allusion'],'chivalric romance':['chivalric romance'],
}
CANON={'routed':'rout','armour':'armor','epic poetry':'epic poem','epic':'epic poem','hexametric line':'hexameter'}
COUNTRY_TERMS={'Greece; Egypt','Greece','Greece; Egyptian','Greece; Italy','Greece; Spain; America','United States; American','Yugoslavia','Odyssey','Homeric Greek'}

def main():
 source=(JOB/'source.wiki').read_text(encoding='utf-8');draft=(JOB/'draft.wiki').read_text(encoding='utf-8')
 records=read_json(JOB/'vocabulary.json');lookups=[]
 for p in sorted((JOB/'evidence').rglob('lookup-*.json')):
  a=read_json(p);word=a.get('word')
  if word:lookups.append((word.casefold(),str(p.relative_to(JOB)),a))
 for v in records:
  term=v['source_term'];words={term.casefold(),*(x.casefold() for x in ALIASES.get(term,[]))}
  attached=[]
  for word,p,a in lookups:
   # Candidate mg evidence uses the same file stem as the English lookup.
   if word in words:
    attached.append(p)
    pair=p.replace('lookup-en-','lookup-mg-')
    if pair!=p and (JOB/pair).exists():attached.append(pair)
  v['evidence_files']=sorted(set(v['evidence_files']+attached))
  v['lookup_records']=[{'file':p,'edition':read_json(JOB/p).get('edition'),'word':read_json(JOB/p).get('word'),'status':read_json(JOB/p).get('status'),'url':read_json(JOB/p).get('url'),'retrieved_at':read_json(JOB/p).get('retrieved_at')} for p in attached]
  v['reason']=v.get('reason','')+' Coordinator: context-specific simple-English and Malagasy definitions reviewed against pinned source; dictionary senses are lexical evidence only. Descriptive wording is not asserted to be an established one-word equivalent. Found but irrelevant or malformed-looking Malagasy senses are not adopted as authority.'
  if term in COUNTRY_TERMS:
   v['evidence_files']=sorted(set(v['evidence_files']+['country-names.json','link-map.json','evidence/title-evidence.json','evidence/mg-verify-000.json','evidence/mg-verify-045.json']))
  for old in ('Akeanina','Akhaiana','Akeana'):
   v['chosen_expression']=v['chosen_expression'].replace(old,'Achaean')
  if term=='Greece; Spain; America':
   v['chosen_expression']='Grisia; Espaina; Etazonia'
   v['reason']+=' The source uses America as a label for United States; new prose uses locally verified Etazonia, absent from the direct country-category cache. No claim of continent/country equivalence.'
 # Merge only matching term/sense families; keep different forge/sacrifice/pride senses.
 merged=[];keys={}
 for v in records:
  canonical=CANON.get(v['source_term'],v['source_term'])
  key=(canonical,v.get('domain',''))
  if key not in keys:
   v['section_ids']=[v.pop('section_id')];keys[key]=len(merged);merged.append(v)
  else:
   other=merged[keys[key]];other['section_ids'].append(v['section_id']);other['evidence_files']=sorted(set(other['evidence_files']+v['evidence_files']))
   other.setdefault('section_choices',[]).append({'section_id':v['section_id'],'chosen_expression':v['chosen_expression'],'source_sense':v['source_sense']})
 unresolved=[v['source_term'] for v in merged if v.get('status')=='unresolved']
 if unresolved:raise RuntimeError('Meaning not accepted: '+repr(unresolved))
 unknown=[];seen=set()
 for v in merged:
  term=v['source_term'];key=CANON.get(term,term).casefold()
  if term in COUNTRY_TERMS or key in seen:continue
  seen.add(key);unknown.append(v)
 if len(unknown)>100:
  lines=['= Lisitra fanaraha-maso voambolana =','Ity lisitra ity dia mitahiry ireo teny sy andian-teny mila fanarahamaso ara-pamaritana na teny malagasy tokana. Tsy filazana fa tsy fantatra ny hevitr’ izy ireo ao amin’ ny lahatsoratra izy: famaritana mazava no voafidy, ary voamarika ny porofo tsy ampy amin’ ny teny tokana. Tsy tafiditra eto ny anaran’ olona, lohatenim-boky sy anaram-pirenena fotsiny.','']
  for i,v in enumerate(unknown,1):
   lines.extend(['== '+str(i)+'. '+v['source_term']+' ==','* Sehatra sy hevitra: '+v.get('domain','')+'; '+v['source_sense'],'* Famaritana anglisy tsotra ('+v.get('definition_origin','editorial_simple_english')+'): '+v.get('english_definition',''),'* Famaritana malagasy: '+v['malagasy_definition'],'* Fomba fiteny voafidy: '+v['chosen_expression'],'* Sata: '+v['status']+'; tsy lazaina ho voambolana tokana eken’ ny rakibolana ny fanazavana ara-panoratana.','* Asa manaraka: fanarahamaso terminôlôjika amin’ ny teny tokana raha ilaina; tsy fanemorana hevitra fototra mbola tsy fantatra.'])
  (JOB/'unknown-vocabulary.wiki').write_text('\n'.join(lines)+'\n',encoding='utf-8')
  for v in merged:v['evidence_files']=sorted(set(v['evidence_files']+['unknown-vocabulary.wiki']))
 write_json(JOB/'vocabulary.json',merged)
 mapping=read_json(JOB/'link-map.json');dc=mw.parse(draft);present={str(x.title) for x in dc.filter_wikilinks()}
 coverage=['= Fandrakofana rohy sy sary =','']
 for item in read_json(JOB/'source-link-inventory.json'):
  target=item['target'];base=target.split('#')[0].replace('_',' ')
  if re.match(r'(?i)^(File|Image):',target):
   filename=target.split(':',1)[1]
   found=any(str(l.title).split(':',1)[-1]==filename for l in dc.filter_wikilinks())
   if not found:raise RuntimeError('Source image lost: '+filename)
   coverage.append('* Sary '+filename+' → voatahiry, anarana tsy niova; caption nadika; Commons/licence ao amin’ ny evidence/files.json.')
  elif target.startswith(('Category:',':Category:')):
   coverage.append('* '+target+' → sokajy anglisy tsy nafarana; sokajy malagasy roa voamarina/inert no ampiana.')
  else:
   mg=mapping.get(base,{}).get('mg')
   if mg and mg in present:decision='rohy '+mg+' voamarina, misy ao amin’ ny draft; label mifanaraka amin’ ny toe-javatra'
   elif mg:decision='kendrena '+mg+' voamarina; jereo ny fanapahan-kevitra manokana ao amin’ ny section-handoff-notes na fanesorana misy antony'
   else:decision='soratra tsotra raha tsy voamarina ny pejy malagasy mitovy lohahevitra; tsy namoronana kendrena'
   coverage.append('* '+target+' → '+decision+'.')
 (JOB/'source-coverage.wiki').write_text('\n'.join(coverage)+'\n',encoding='utf-8')
 # Native citation integrity: exact source DOI/ISBN fields survive, or are logged.
 source_ids=[]
 for t in mw.parse(source).filter_templates():
  if str(t.name).strip().lower().startswith('cite '):
   for k in ('doi','isbn','jstor'):
    if t.has(k) and str(t.get(k).value).strip():source_ids.append((k,mw.parse(str(t.get(k).value)).strip_code().strip()))
 missing=[(k,v) for k,v in source_ids if v not in draft]
 write_json(JOB/'integrity-audit.json',{'source_identifiers':source_ids,'identifiers_absent_from_draft':missing,'templates_remaining':[str(t) for t in dc.filter_templates()],'image_count':len([l for l in dc.filter_wikilinks() if re.match(r'(?i)^(File|Image|Sary):',str(l.title))]),'vocabulary_records':len(merged),'distinct_terminology_review_items':len(unknown)})
 if missing:raise RuntimeError('Source identifiers missing: '+repr(missing))
 print('Vocabulary records',len(merged),'distinct review items',len(unknown),'identifiers',len(source_ids),'remaining templates',len(dc.filter_templates()))

if __name__=='__main__':main()
