"""Offline inventory and exclusive section assignments for Iliad."""
import shutil
from pathlib import Path
import mwparserfromhell as mw
from mgwiki_editor.core import read_json, write_json

JOB = Path('runs/iliad-en-20261106')
PLAN = [
 ('00-lead',1,44,'Fampidirana sy mombamomba ny tononkalo'),
 ('01-exposition',45,67,'Famintinana: fiandohana'),
 ('02-duels',68,74,'Adin’ ny mahery fo'),
 ('03-rout',75,91,'Faharesen’ ny Grika'),
 ('04-patroclus',92,108,'Fahafatesan’ i Patroclus'),
 ('05-achilles',109,123,'Hatezeran’ i Achilles'),
 ('06-religion',124,153,'Lohahevitra: fivavahana'),
 ('07-fate',154,203,'Lahatra'),
 ('08-kleos-nostos',204,234,'Voninahitra sy fiverenana an-tanindrazana'),
 ('09-pride-hybris',235,254,'Avonavona, herim-po, haja ary hybris'),
 ('10-menis-war',255,288,'Hatezerana sy ady'),
 ('11-history',289,307,'Daty sy tantaran’ ny lahatsoratra'),
 ('12-oral',308,318,'Lovantsofina am-bava'),
 ('13-combat',319,366,'Fanehoana ny ady sy fanamboarana fitaovam-piadiana'),
 ('14-military-influence',367,402,'Fiantraikany tamin’ ny ady grika'),
 ('15-culture',403,419,'Fiantraikany ara-javakanto sy ara-kolontsaina'),
 ('16-english-arts',420,424,'Zavakanto anglisy'),
 ('17-twentieth',425,441,'Zavakanto tamin’ ny taonjato faha-20'),
 ('18-contemporary',442,455,'Kolontsaina malaza ankehitriny'),
 ('19-sciences',456,458,'Siansa'),
 ('20-gender',459,474,'Fanehoana ny vehivavy sy ny lehilahy'),
 ('21-translations',475,502,'Dikan-teny anglisy'),
 ('22-manuscripts',503,513,'Sora-tanana'),
 ('23-related',514,523,'Jereo koa'),
 ('24-references',524,556,'Fanamarihana, loharano ary boky'),
 ('25-reading',557,578,'Boky sy lahatsoratra fanampiny'),
 ('26-external',579,620,'Rohy ivelany sy sokajy'),
]

def main():
 s=(JOB/'source.wiki').read_text(encoding='utf-8'); lines=s.split('\n'); code=mw.parse(s)
 records=[]
 for sid,start,end,heading in PLAN:
  d=JOB/'sections'/sid; d.mkdir(parents=True,exist_ok=True)
  (d/'source.wiki').write_text('\n'.join(lines[start-1:end])+'\n',encoding='utf-8')
  records.append(dict(id=sid,start=start,end=end,heading=heading,directory=str(d),status='pending',local_context='No existing Iliady mainspace or Iliasy sandbox text.'))
 write_json(JOB/'section-plan.json',records)
 write_json(JOB/'source-link-inventory.json',[dict(target=str(x.title),label=str(x.text or x.title)) for x in code.filter_wikilinks()])
 write_json(JOB/'citation-inventory.json',[str(t) for t in code.filter_templates() if str(t.name).strip().lower().startswith('cite ')])
 refs=[str(t) for t in code.filter_tags() if str(t.tag).lower()=='ref' and t.has('name') and not t.self_closing]
 (JOB/'shared-references.wiki').write_text('\n\n'.join(refs),encoding='utf-8')
 shutil.copyfile('data/country-names.json',JOB/'country-names.json')
 for f in ('iliad-langlink.json','iliad-title-search.json','iliasy-title.json'):
  shutil.copyfile(Path('/tmp/opencode')/f,JOB/f)
 (JOB/'shared-context.wiki').write_text("""= Shared section context =
Title: Iliasy, a user-authorized Malagasy working title, not a claim of a published edition. Iliady is attested in the local article Boky. No mg interlanguage link from English Iliad. Existing Iliady and exact Iliasy sandbox are empty. Coordinator checks alternate title pages separately.
Only write section.wiki, notes.wiki and vocabulary.json in YOUR assigned sections directory. No network, no nested agents, no shared writes, no publication. Read the three required skills and both style references. Full natural Malagasy prose, amin' ny apostrophe spacing. Title mentions ''Iliasy''; Odyssey = ''Odisey'' where local evidence supports it. Preserve names such as Achilles, Hector, Agamemnon, Homer rather than guessing Malagasy transcriptions; Latin-script source names are acceptable. Greek technical words italicized and explained; Greek originals in direct quotations retained, and supplied romanizations used in prose. Record needs for missing romanizations.
Country names: cached Grisia, Ejipta, Frantsa, Alemaina, Italia, Iogôslavia, etc.; see country-names.json. Do not change original titles, citation metadata, filenames or URLs.
Preserve all source internal links provisionally with translated labels and their EXACT English targets. Coordinator maps them to verified mg topics or documents unlinked fallback. Do not invent new targets. Include every image unchanged filename and translate captions. Infobox -> native wikitable if local template unverified. Preserve all data; omit maintenance/navbox/authority templates with notes. Categories inert, no guessed mg categories.
Preserve citation templates literally for coordinator's native adaptation; preserve named ref definitions/reuses and exact metadata. Cross-section refs in shared-references.wiki. West2011 is duplicated identically in lead and must be deduplicated at integration. :9 defined in gender after first use there. :5 is reused before definition in oral section. Notes use native <ref group=\"fanamarihana\"> and renderer in appendices. Source short references will be converted centrally. Do not invent missing page numbers or years.
Copyright: avoid translating the source's many long excerpts of copyrighted modern translations wholesale. Summarize long quotations accurately in original Malagasy prose, attribute to the named translation, retain verse numbers and citations; record each selective quotation/paraphrase decision. Short necessary linguistic comparison quotations in gender can remain verbatim with contextual Malagasy explanations; do not sanitize. Ancient Greek original quotations may be preserved. Distinguish quoted evaluations from facts.
Source includes substantial unsourced interpretation (heroism, timē, war etc.) and maintenance flags. Do not pretend these are well-sourced. Faithfully preserve supported narrative facts, flag unsupported authorial-intent/consensus/living-person judgments and source contradictions in notes, without guessing authority or silently strengthening claims. Coordinator decides gate. In history source links terminus ante quem to wrong terminus post quem; use accurate sense 'latest possible date', flag target mismatch. Source first printed edition 1489 may conflict with historical evidence; do not change without evidence, flag. Gender calls Christa 'Wolfe' once; source itself elsewhere consistently Wolf: use Wolf. Science PTSD needs Malagasy transcription plus (na explanation); moral injury is not itself a diagnosis.
For unfamiliar vocabulary write simple-English sense definition then Malagasy definition, label editorial definitions honestly, add lookup requests to notes for coordinator. Existing shared dictionary evidence will be pinned centrally; do not claim dictionary verification yourself. Material unresolved meanings block. No research placeholders in fragment prose.
""",encoding='utf-8')
 state=read_json(JOB/'job.json')
 notes=['= Fanamarihana momba ny fanitsiana =','', '== Fidirana sy porofo ==',f"Loharano: {state['source']['url']}; Wikipedia contributors; CC BY-SA. Hotehirizina ao amin’ ny edit summary ny permanent link.",'Novakiana tanteraka ny source.wiki sy ireo snapshot existing.wiki ary sandbox.wiki samy banga. Iliasy tsy misy; Iliady tsy misy. Hojerena koa ny fanoratra sy sandbox hafa. Ny lohateny Iliasy dia naroson’ ny mpampiasa; tsy lazaina ho lohatenin’ ny dikan-teny efa navoaka.','Tsy nosokafana ny rohy ivelany; metadata voatahiry ihany. Ny init voalohany dia tapitra alohan’ ny famoronana job noho ny langlinks namorona sites maro; nalaina tamin’ ny query lllang=mg tokana ny porofo fa tsy misy mg langlink, ary init explicit existing-title no nahomby. Tsy nisy write na cooldown nolalovana.','','== Drafitra isam-pizarana ==']
 for r in records: notes.append(f"* {r['id']}: {r['start']}–{r['end']}; {r['heading']}; {r['directory']}; miandry. Miankina amin’ ny references sy fanamarinana rohy iombonana; tsy misy local text.")
 (JOB/'notes.wiki').write_text('\n'.join(notes)+'\n',encoding='utf-8')
 print(len(records),'sections planned')

if __name__=='__main__': main()
