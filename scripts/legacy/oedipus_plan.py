"""Create offline section assignments and shared editorial instructions."""
from pathlib import Path
import json

JOB = Path('runs/oedipus-20261105')
PLAN = [
    ('00-lead', 1, 26, 'Fampidirana sy mombamomba'),
    ('01-basics', 27, 51, 'Fototry ny angano'),
    ('02-ancient', 52, 78, 'Loharano tamin’ ny Andro Taloha; Odysseus sy Pindar'),
    ('03-aeschylus', 79, 84, 'Ny trilojian’ i Aeschylus'),
    ('04-sophocles', 85, 87, 'Ny tantara an-tsehatra nosoratan’ i Sophocles'),
    ('05-rex', 88, 97, 'Oedipus Rex'),
    ('06-colonus', 98, 101, 'Oedipus at Colonus'),
    ('07-antigone', 102, 107, 'Antigone'),
    ('08-euripides', 108, 115, 'Ny sanganasan’ i Euripides'),
    ('09-playwrights', 116, 118, 'Mpanoratra tantara an-tsehatra hafa'),
    ('10-additions', 119, 126, 'Fanampiana tatỳ aoriana'),
    ('11-literature', 127, 134, 'Literatiora taorian’ ny vanim-potoana klasika'),
    ('12-family', 135, 138, 'Tetiarana'),
    ('13-complex', 139, 143, 'Ny complexe d’ Œdipe'),
    ('14-related', 144, 151, 'Jereo koa'),
    ('15-references', 152, 163, 'Fanamarihana sy loharano'),
    ('16-external', 164, 189, 'Rohy ivelany sy fifandimbiasana'),
]


def main():
    lines = (JOB / 'source.wiki').read_text(encoding='utf-8').splitlines(keepends=True)
    records = []
    for ident, start, end, heading in PLAN:
        directory = JOB / 'sections' / ident
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'source.wiki').write_text(''.join(lines[start-1:end]), encoding='utf-8')
        records.append(dict(id=ident, start=start, end=end, heading=heading,
                            directory=str(directory), status='pending'))
    (JOB / 'section-plan.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    notes = """= Fanamarihana momba ny fanitsiana =
== Fanasokajiana sy fiaviana ==
Pejy efa misy: Œdipe. Porofo: rohy mg an’ ny pejy anglisy sy existing.wiki. Tsy misy lahatsoratra ao amin’ ny sandbox. Loharano anglisy: https://en.wikipedia.org/w/index.php?oldid=1383116149 ; mpandray anjara ao amin’ ny Wikipedia anglisy, CC BY-SA 4.0. Ny famintinana fanovana dia hitanisa ny fiavian’ ny fandikan-teny.
Ny andinin-teny eo an-toerana momba an’ i Laius, Jocasta sy ireo zanaka efatra dia ampidirina ao amin’ ny fampidirana sy ny tabilao; tsy misy loharano fanampiny ao amin’ ny pejy mg. Hotehirizina ny Biôgrafia, ny rohy Freebase sy ny sokajy efa misy; tsy adika ny infobox tsy feno sy ny marika vangovango fa soloina votoaty feno sy tabilao tsotra.
== Olana hita sy fanapahan-kevitra ==
Tsy sokafana ireo rohy ivelany, boky, DOI na sary. Ny metadata voatahiry ihany no porofo momba ny rakitra.
Source line 56 explicitly flags the Laius journey to solve the Sphinx riddle as failed verification: omit that alternative and its unsupported Sophocles 132–137 citation; preserve the separately cited alternative that he sought news of his son (Euripides 35–38). This is an explained exclusion, not a claim that the failing citation was verified.
Source line 54 first dates written mention to fifth century BC while crediting Homer and later quoting Odyssey. Do not repeat that internally conflicting first-attestation date; preserve oral transmission, attribution to Homer, and subsequent sources without inventing a replacement date.
Foreign navigation/maintenance/authority templates are not article prose and will not be imported; family-tree data and succession data will be adapted to native tables. Source portals can be represented as plain related subjects if local targets unavailable. Category targets from the source are not imported by guessing.
== Drafitra fizarana ==
"""
    for r in records:
        notes += f"* {r['id']}: source.wiki {r['start']}–{r['end']}; {r['heading']}; {r['directory']}; miandry. 00 mitambatra amin’ ny fianakaviana ao existing.wiki; 14 sy 16 mitahiry rohy eo an-toerana. 05–07 miankina amin’ ny lohateny ambaratonga fahatelo ao 04; ny hafa mahaleo tena.\n"
    (JOB / 'notes.wiki').write_text(notes, encoding='utf-8')
    (JOB / 'shared-context.wiki').write_text("""= Toromarika iombonana =
Translate only your assigned section from sections/ID/source.wiki. Coordinator has read all source/existing/sandbox snapshots. Existing is a stub, no sandbox. Article title and main label: Œdipe; keep original personal names as source spells them except this locally verified topic name. Latin source romanization Oidípous can be retained with original Greek as optional supplied name.
Read link-map.json and evidence/files.json when available. A non-null mg mapping is verified source interlanguage evidence; do not guess any other link. For null/missing mappings use translated plain text and list every source-target fallback in your notes. Do not use English wiki links as if mg links. Same-page title anchors must be translated; source Sophocles#Theban plays has a cross-page anchor not a local heading.
All six source images must survive, with identical Commons filenames, translated meaningful captions/alt text; native File markup, no downloading. The lead image belongs in 00. Only native wikitext, no unverified local templates: citation templates convert faithfully to literal bibliographic refs (all metadata and URLs); <nowiki>ISBN ...</nowiki> avoids tracking categories.
Review source problems in root notes.wiki. 02-ancient must exclude the explicitly failed-verification Sphinx-journey clause/citation and the internally inconsistent first-written-fifth-century date, documenting exclusions. Keep other claims and citations. Do not silently repair other material conflicts: report them to coordinator.
Preserve source work titles and bibliographic metadata. Titles use italics in narrative, translated explanatory gloss only if needed. No unmarked English prose. Greek technical word aphar has no source romanization; explain «avy hatrany» without copying Greek into new prose, but record omitted dictionary-link target.
Basic shared terms: angano grika (Greek mythology); mpanjaka; faminaniana (prophecy); famaliana avy amin’ ny andriamanitra / toerana ilazana izany (oracle, contextual); firaisana ara-nofo eo amin’ ny mpihavana akaiky (incest); fampisehoana mampalahelo / loza manjo ny mahery fo (tragedy in context); trilogy = trilojia (tantara an-tsehatra telo mifampitohy). Do not equate satyr play with satire: describe a play with satyrs. Infertility in the plague is tsy fahafahan’ ny zavamananaina miteraka; do not turn an unspecified mythic plague into medically confirmed plague disease. Neurosis and Oedipus complex must be simple explanatory terms framed as Freud’s account, not a modern diagnosis of the mythic character.
Source names Laius, Jocasta, Polybus, Merope, Creon, Sophocles, Aeschylus, Euripides, Pindar, Homer retained in that form; source work titles retained. Use source-supported other names, no guessed Malagasy transliteration. Prefix i before names naturally. Apostrophes in new Malagasy prose have one following space, never mutate original titles/metadata/URLs.
Named references across sections: Wilson is defined in 01; Euripides, Phoenissae defined in 02; :0 defined and reused in 04. There are no cross-section reuses needing extra definitions. Preserve all unnamed refs. Fragment 15 contains <references />.
Output only in your exclusive sections/ID/ directory: section.wiki, notes.wiki, vocabulary.json. Vocabulary records are sense-specific, labelled editorial if no dictionary definition; point to already pinned lookup evidence, report missing lookup needs in notes. Never fetch anything or call other agents; no shared-file writes. Do not set article review gates or publish. Missing evidence must be reported, not invented.
00: use simple native infobox-equivalent wikitable including all source fields and one lead image. Preserve local family facts in lead/table.
04: == ancestor heading is supplied by 02; your heading is === ; 05–07 are ==== under 04.
12: read evidence/family-template.wiki completely and adapt the actual family relations into clear native wikitable(s), preserving variant legend and all ancestors/descendants/links. No guessed links or relations.
14: preserve existing [[Biôgrafia]] in addition to source related subjects. Commons can be an explicit inert interwiki link [[:commons:Category:Oedipus|...]]; no categorizing templates.
16: preserve local [https://www.freebase.com/m/0k8pc Freebase] entry without claiming the URL works. Adapt source succession box to simple native table, retaining Laius/Creon conflict with lead Eteocles as distinct source presentation rather than merging into one unsupported chronology. End with [[:sokajy:Biôgrafia]] exactly preserving category target capitalization and order. No other category unless coordinator supplies verified evidence.
""", encoding='utf-8')


if __name__ == '__main__':
    main()
