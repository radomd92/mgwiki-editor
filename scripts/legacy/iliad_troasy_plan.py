"""Plan a section-limited, protection-aware name revision; no remote operations."""
import re
import shutil
import textwrap
from pathlib import Path
import mwparserfromhell as mw
from mgwiki_editor.core import read_json, write_json, digest

JOB=Path('runs/iliad-troasy-20261106')
PRIOR=Path('runs/iliad-en-20261106-r1')
STARTS=[
 ('00-lead',None),('01-exposition','== Famintinana =='),
 ('02-duels',"=== Adin' ny mahery fo (boky faha-5–7) ==="),
 ('03-rout',"=== Faharesen' ny Grika (boky faha-8–15) ==="),
 ('04-patroclus',"=== Fahafatesan' i Patroclus (boky faha-16–18) ==="),
 ('05-achilles',"=== Hatezeran' i Achilles (boky faha-19–24) ==="),
 ('06-religion','== Lohahevitra =='),('07-fate','=== Lahatra ==='),
 ('08-kleos-nostos','=== Voninahitra sy fiverenana an-tanindrazana ==='),
 ('09-pride-hybris',"=== Avonavona, herim-po, haja ary ''hybris'' ==="),
 ('10-menis-war',"=== Hatezerana (''mēnis'') ==="),
 ('11-history',"== Daty sy tantaran' ny lahatsoratra =="),
 ('12-oral','=== Lovantsofina am-bava ==='),
 ('13-combat','== Fanehoana ny ady sy fanamboarana fitaovam-piadiana =='),
 ('14-military-influence',"=== Fiantraikany tamin' ny ady grika ==="),
 ('15-culture','== Fiantraikany ara-javakanto sy ara-kolontsaina =='),
 ('16-english-arts','=== Zavakanto anglisy ==='),
 ('17-twentieth','=== Zavakanto tamin’ ny taonjato faha-20 ==='),
 ('18-contemporary','=== Kolontsaina malaza ankehitriny ==='),
 ('19-sciences','=== Siansa ==='),('20-gender','== Fanehoana ny vehivavy sy ny lehilahy =='),
 ('21-translations','== Dikan-teny anglisy =='),('22-manuscripts','== Sora-tanana =='),
 ('23-related','== Jereo koa =='),('24-references','== Fanamarihana =='),
 ('25-reading','== Boky sy lahatsoratra fanampiny =='),('26-external','== Rohy ivelany ==')]
STARTS=[(i,s.replace('’',"'") if s else s) for i,s in STARTS]
NAME=re.compile(r'\b(?:Troy|Troie|Trôia)\b')
QUOTE=re.compile(r'("[^"\n]*"|«[^»]*»|“[^”]*”)')

def revise_name(text):
 code=mw.parse(text);changes=[]
 # Quote protection must span AST node boundaries: a wikilink may occur inside
 # guillemets. A text-node-only walker would miss that quotation context.
 protected=[m.span() for m in QUOTE.finditer(text)]
 def protect_literal(value):
  protected.extend(m.span() for m in re.finditer(re.escape(value),text))
 for tag in code.filter_tags():
  if str(tag.tag).lower() in {'ref','references','nowiki','i','b','math','chem'}:protect_literal(str(tag))
 for link in code.filter_external_links():protect_literal(str(link.url))
 for match in re.finditer(r'\[\[([^\]|\n]+)',text):protected.append(match.span(1))
 for link in code.filter_wikilinks():
  if link.text is None and str(link.title) in {'Troy','Troie','Trôia'}:
   raise RuntimeError('Default city label needs a separately reviewed explicit label')
 pieces=[];cursor=0
 for match in NAME.finditer(text):
  if any(a<=match.start()<b for a,b in protected):continue
  pieces.extend((text[cursor:match.start()],'Troasy'));cursor=match.end()
  changes.append({'old':match.group(),'new':'Troasy','count':1,'start_char':match.start(),'end_char':match.end()})
 pieces.append(text[cursor:])
 return ''.join(pieces),changes

def readable(text):
 return '\n'.join('\n'.join(textwrap.wrap(l,130,break_long_words=False,break_on_hyphens=False,replace_whitespace=False,drop_whitespace=False)) for l in text.split('\n'))

def main():
 state=read_json(JOB/'job.json');previous=read_json(PRIOR/'job.json');receipt=read_json(PRIOR/'receipt.json')
 assert state['source']['sha256']==previous['source']['sha256']
 assert state['sandbox']['sha256']==receipt['draft_sha256'] and state['sandbox']['revision_id']==receipt['revision_id']
 assert not state['existing']['text']
 text=state['sandbox']['text'];positions=[0 if h is None else text.index(h+'\n') for _,h in STARTS]+[len(text)]
 assert positions==sorted(positions)
 oldplan={r['id']:r for r in read_json(PRIOR/'section-plan.json')};en=state['source']['text'].split('\n');plan=[]
 for i,(sid,heading) in enumerate(STARTS):
  d=JOB/'sections'/sid;d.mkdir(parents=True,exist_ok=True);fragment=text[positions[i]:positions[i+1]]
  candidate,changes=revise_name(fragment) if sid not in {'24-references','25-reading'} else (fragment,[])
  for filename,content in [('source.wiki',fragment),('candidate.wiki',candidate),('source-readable.wiki',readable(fragment)),('candidate-readable.wiki',readable(candidate))]:
   (d/filename).write_text(content,encoding='utf-8')
  a=oldplan[sid];(d/'source-en.wiki').write_text('\n'.join(en[a['start']-1:a['end']]),encoding='utf-8')
  record={'id':sid,'heading':heading or 'lead/infobox','directory':str(d),'start_byte':positions[i],'end_byte':positions[i+1],'source_sha256':digest(fragment.encode()),'replacement_count':sum(x['count'] for x in changes),'status':'pending_worker' if changes else 'unchanged_reused','dependencies':'shared references unchanged; exact join in original order; coordinator-only final review'}
  write_json(d/'candidate-diff.json',changes)
  if not changes:
   (d/'section.wiki').write_text(fragment,encoding='utf-8')
   (d/'notes.wiki').write_text('= Fizarana tsy ovana =\nTsy misy anaran-tanàna mila soloina ivelan’ ny faritra voaaro. Voatahiry byte-for-byte ny fizarana sy references, titles ary categories efa nekena.\n',encoding='utf-8')
   write_json(d/'vocabulary.json',[])
  plan.append(record)
 assert ''.join((JOB/'sections'/r['id']/'source.wiki').read_text(encoding='utf-8') for r in plan)==text
 write_json(JOB/'section-plan.json',plan)
 refs=[str(t) for t in mw.parse(text).filter_tags() if str(t.tag).lower()=='ref' and t.has('name') and not t.self_closing]
 (JOB/'shared-references.wiki').write_text('\n\n'.join(refs),encoding='utf-8')
 for name in ('country-names.json','link-map.json'):
  shutil.copyfile(PRIOR/name,JOB/name)
 for name in ('vocabulary.json','review.json','receipt.json','proposal.json'):
  shutil.copyfile(PRIOR/name,JOB/('prior-'+name))
 d=JOB/'naming-evidence';d.mkdir(exist_ok=True)
 for name in ('mg-verify-000.json','mg-verify-045.json'):
  shutil.copyfile(PRIOR/'evidence'/name,d/name)
 (JOB/'user-request.wiki').write_text('= Fangatahan’ ny mpampiasa =\ncan you use Troasy for the name of troy?\n\nTroasy = anaran’ ilay tanàna antsoina hoe Troy ao amin’ ny Iliasy; safidin’ ny mpampiasa, tsy filazana fanoratana ofisialy. Tsy fanovana anaran-pejy na bibliographic titles no nangatahina.\n',encoding='utf-8')
 (JOB/'shared-context.wiki').write_text("""= Narrow naming revision =
User requests Troasy for the CITY Troy. Only modify the city's visible name in newly written Malagasy prose/captions. Do NOT rename any page or link target: verified target Trôia stays Trôia, displayed label becomes Troasy. Do NOT change Troiana/Trojan/Trojanina ethnonyms into an invented derivative. Do NOT change foreign book/film/paper/artwork titles (e.g. ''Troy'', ''Helen of Troy'', ''The Women of Troy''), original quotations, <ref> contents/citation metadata, filenames, URLs, identifiers, categories or reference names. No new article facts, no retranslation, no stylistic churn.
The source Wikipedia revision is unchanged, 1383771922. The pinned Malagasy sandbox is EXACTLY the fully reviewed saved previous article, revision1153305. Mainspace Iliasy snapshot is empty. Preserve all prior contributions and the exact text except the requested city-name labels. Prior review/vocabulary/receipt/proposal evidence pinned at root. Country names unchanged, no refresh or terminology lookup needed for this user-supplied proper-name preference.
Each assigned directory contains source.wiki (the exact local section), source-readable.wiki (full soft-wrapped viewing copy), source-en.wiki (matching English source context), candidate.wiki and candidate-readable.wiki (a mechanical protection-aware proposed edit). Coordinator made candidate only as an editing aid, NOT final editorial approval. Read the FULL source and candidate, using readable copies if long lines truncate. Check every proposed replacement and protect all exceptions. Keep exact leading/trailing whitespace and final-newline state. If correct you may copy candidate bytes to section.wiki; do not regenerate prose. If a naming occurrence missed by candidate is genuinely city prose, record need rather than inventing a change to protected text. Glosses inside quotation marks are conservatively preserved as quotations.
Only write section.wiki, notes.wiki, vocabulary.json in YOUR assigned directory. No remote requests, nested agents, shared writes, prepare/publish, or modification of source/candidate evidence. Coordinator merges and reviews. References are unchanged; shared-references.wiki provides cross-section definitions, no new references or renderers. Independent workers offline only.
Vocabulary notes: source_term Troy; simple English definition 'The ancient city besieged in the Trojan War and named in the Iliad.'; Malagasy definition 'Ilay tanàna fahiny natao fahirano tamin’ ny ady tantaraina ao amin’ ny Iliasy.'; chosen Troasy, descriptive user-requested spelling, NOT dictionary verified or an asserted official local title. Existing local page identity verified as Trôia. No dictionary lookup required for this explicit proper-name preference. All three skills and full local style manuals apply; they were already read by the coordinator in this conversation.
""",encoding='utf-8')
 notes=['= Fanitsiana voafetra: Troy ho Troasy =','',f"Loharano anglisy: {state['source']['url']}; sandbox base: {state['sandbox']['url']}.",'Novakiana teo aloha tanteraka ny source sy ny lahatsoratra nekena; mitovy byte-for-byte amin’ ireo votoaty efa voavaky ny snapshots vaovao araka ny hashes sy text comparison. Novakiana ny mainspace snapshot vaovao banga. Tsy misy local contribution vaovao very; ny base sandbox manontolo no zaraina ho fizarana mifanesy tsy misy banga. Tsy misy fandalinana ivelany na raw HTTP.','Fanovana anaran-tanàna hita maso ihany no scope. Arovan’ ny famaritana ny original titles, quotations, metadata, link targets, filenames, URLs, identifiers sy categories. Troasy dia safidin’ ny mpampiasa fa tsy anarana ofisialy lazaina ho voamarina.','','== Drafitra isam-pizarana ==']
 for r in plan:notes.append(f"* {r['id']}: {r['heading']}; {r['directory']}; {r['status']}; fanoloana {r['replacement_count']}; refs sy filaharana tsy miova.")
 (JOB/'notes.wiki').write_text('\n'.join(notes)+'\n',encoding='utf-8')
 print('Assignments requiring workers:')
 for r in plan:
  if r['status']=='pending_worker':print(r['id'],r['replacement_count'])
 print('Total replacements',sum(r['replacement_count'] for r in plan),'sections',len(plan))

if __name__=='__main__':main()
