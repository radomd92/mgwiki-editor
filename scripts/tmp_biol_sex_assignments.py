"""Write per-section worker assignments (offline, exclusive output dirs)."""
from pathlib import Path

job = Path("runs/biol-sex-20261114")
common = """# Section assignment: {sid}

You are an offline mgwiki-section worker. Work only in this job and only in this
directory. Do not read or write shared job files outside your directory. Do not
use the network, Wikipedia, dictionaries, shell helpers, or nested agents. Do not
publish. The coordinator owns all remote operations and final assembly.

## Inputs

- Pinned source section: `{src}` (read it completely).
- Shared job notes: `../../notes.wiki` (read title, plan, link/image inventory).
- Shared terminology memo: `../../terminology.md` (follow it).
- Verified en->mg link mapping: `../../evidence-link-targets.json`. Use only
  records whose `mg_title` is non-null. For all other link targets, write plain
  text; never guess a Malagasy title.
- File metadata evidence: `../../evidence-file-metadata.json`.
- Template existence evidence: `../../evidence-template-info.json`.
- {extra}

## Required outputs (write only here)

- `section.wiki`: the Malagasy translation of this section, MediaWiki wikitext
  only. No Markdown, no code fences, no prose wrapper.
- `notes.wiki`: plain text/Markdown notes: coverage checklist, image/link mapping,
  template decisions, source issues, uncertainties, references used.
- `vocabulary.json`: JSON array of section-local vocabulary records, same fields
  as mg-vocab (source_term, source_language, domain, source_sense,
  english_definition, definition_origin, malagasy_definition, chosen_expression,
  evidence_files, alternatives_rejected, status, reason). Use local evidence paths
  only. Do not duplicate shared records already in `../../vocabulary.json`; add
  only new or section-specific terms.

## Translation rules

- Translate every sentence and claim in the assigned source, preserving negation,
  qualifications, numbers, dates, attribution and uncertainty. Do not add claims,
  diagnoses, advice, or translator commentary.
- Natural standard Malagasy; neutral encyclopedic register. New prose uses one
  space after Malagasy elision apostrophes: `amin' ny`, `an' Andriamanitra`,
  `amin' izao`, `tamin' ny`, `ho an' ny`.
- Translate headings, captions, alt text, table text and link labels. Keep
  Commons filenames unchanged.
- Retain foreign terms/acronyms with a Malagasy gloss on first mention; italicize
  retained foreign words/phrases with `''...''`. Medical/biological first
  mentions use `[Malagasy term] (na [Malagasy explanation])`; English may follow.
- Keep citation metadata, quotation wording, original titles, URLs, DOIs, ISBNs,
  filenames, identifiers and exact link targets unchanged. Do not open URLs.
- Preserve every `<ref>` block at its claim. For named references, copy the
  definition exactly where the source defines it; keep `<ref name="X" />` reuses.
  Do not translate inside citation templates. The coordinator deduplicates.
- Include every image from the assigned source range with a translated caption.
  If a source template is unsupported locally, use simple `[[Sary:...|thumb|...]]`
  or a plain wikitable; record the adaptation in notes.wiki.
- Hatnotes: use `{{lahatsoratra antsipirihany|Target}}` only for a verified
  Malagasy target. If none is verified, omit the hatnote and record why. Never
  leave an English `{{Main}}`/`{{Further}}` or a bare English link.
- Internal links: use verified `mg_title` values only; adapt same-page anchors to
  the translated headings in this article. Otherwise plain text.
- Category links are coordinator-only; do not add Sokajy in section.wiki.

## Section-specific instructions

{specific}
"""

sections = {
    "00-lead": dict(
        src="source.wiki", extra="No supplement.",
        specific="""Source lines 1-13. Translate the four lead paragraphs (the source
infobox/sidebar, short description and redirect/maintenance templates are omitted).
Bold the article title `'''Lahy sy vavy ara-biôlôjika'''` at first mention. Define
the topic as the biological trait of producing male or female gametes. Keep the
source's note that the term "biological sex" is used when "sex" alone is ambiguous;
render it descriptively without importing the English disambiguation page. Do not
add a heading. Do not add images. Lead should summarize the body: sexual
reproduction, sex-determination systems, dimorphism, and organisms without
male/female gamete sizes (mating types).""",
    ),
    "01-sexual-reproduction": dict(
        src="source.wiki", extra="No supplement.",
        specific="""Source lines 14-70. Headings: `== Fananahana ara-nofo ==`,
`=== Biby ===`, `=== Zavamaniry ===`, `=== Holatra ===`. Translate the intro and
all three subsections completely. Include the four images in this range
(Sexual cycle.svg; Hoverflies mating midair.jpg; Mature flower diagram.svg;
Pinus nigra cone.jpg + Pine cones, immature male.jpg as the source multiple-image
pair). The multiple-image template is missing locally; use two separate thumbnails
or a simple wikitable with translated captions. Preserve the source's plant/fungi
detail, including flower parts, cones, pollination, isogamy/anisogamy, yeast mating
types, and fungal spores. Hatnotes: source Main Sexual reproduction, Main Sexual
reproduction#Animals, Main Plant reproduction, Main Mating in fungi; no verified
mg targets, so omit the hatnotes and record that in notes.wiki. Keep all refs.""",
    ),
    "02-sexual-systems": dict(
        src="source.wiki", extra="No supplement.",
        specific="""Source lines 71-80. Headings: `== Rafi ara-pananahana ==`,
`=== Biby ===`, `=== Zavamaniry ===`. Translate the definition of a sexual system,
the 95%/5% animal figures and the vertebrate/fish statement, and the plant
bisexual/monoecious/dioecious material including the 5%, 5000-origins and 65%
figures. Include the Monoecy_dioecy_en.svg image with translated alt text and
caption. Source Main Sexual system has no verified mg target; omit hatnote and
record. Keep all refs.""",
    ),
    "03-terminology": dict(
        src="source.wiki", extra="No supplement.",
        specific="""Source lines 81-97. Heading: `== Voambolana ==`. This is a
definition list (`; term` / `: definition`). Translate each defined term and its
definition: genetic sex, chromosomal sex, gonadal sex, gametic sex, phenotypic sex,
anatomical sex, hormonal sex. Preserve the examples (SRY, XX/XY, gonads, biopsy,
intersex, simultaneous hermaphrodites, womb, external genitalia, capon) and the
source's qualifications. Use the shared terminology memo. Keep all refs. No images.""",
    ),
    "04-sex-determination-systems": dict(
        src="source.wiki", extra="No supplement.",
        specific="""Source lines 98-156. Headings: `== Rafi famaritana ny maha-lahy
na maha-vavy ==`, `=== Ara-pototarazo ===`, `==== Famaritana XY ====`,
`==== Famaritana ZW ====`, `==== Famaritana XO ====`, `==== Famaritana ZO ====`,
`=== Ara-tontolo iainana ===`, `==== Hermafrôditisma mifandimby ====`,
`==== Famaritana mifototra amin' ny hafanana ====`, `==== Haplôdiplôidia ====`.
Translate all subsections completely, preserving chromosome notation (XX, XY, ZW,
ZZ, XO, ZO), the platypus ten-chromosome example, fruit-fly exceptions, butterfly
ZW variants, cricket/XO examples, C. elegans, temperature thresholds (22 °C, 28 °C)
and haplodiploidy. Include images: Evolsex-dia2a.svg; Drosophila
XY sex-determination.svg; Chalkhill blue butterflies...; Common clubtail...;
Ceratopteris pteridoides kz02.jpg; Ocellaris clownfish.JPG; Crocoparc Naissance des
bébés.jpg. Source Main Sex-determination system and Main Environmental sex
determination have no verified mg targets; omit hatnotes and record. Keep all refs.""",
    ),
    "05-evolution-of-sex": dict(
        src="source.wiki", extra="No supplement.",
        specific="""Source lines 157-177. Headings: `== Fivoaran' ny lahy sy vavy ==`,
`=== Asa mampifanaraka ny lahy sy vavy ===`. Translate the evolution-of-sex
material: isogamy ancestral to anisogamy, independent origins, origin of male and
female, sexual dimorphism, the 1.2-billion-year Bangiomorpha fossil, green-algae
mating-type evidence, external vs internal fertilization, and the adaptive-function
paragraph (meiosis/genome integrity, recombination, outcrossing, complementation,
genetic variation). Include Anisogamy.svg and Isogamy.svg (source multiple-image
pair) as separate thumbnails or a simple table with translated captions. Source
Main Evolution of sexual reproduction has no verified mg target; omit hatnote and
record. Keep all refs.""",
    ),
    "06-sex-ratio": dict(
        src="source.wiki", extra="Use `supplement.wiki` as the expanded pinned content of the source `{{Excerpt|Sex ratio}}`; translate that prose and its refs. The source section source.wiki only contains the template call.",
        specific="""Source lines 178-180. Heading: `== Tahan' ny lahy sy ny vavy ==`.
The pinned source uses an excerpt transclusion. The coordinator expanded it and
saved the rendered wikitext in `supplement.wiki` (pinned in
`../../evidence-excerpt-expansions.json`). Translate the excerpt prose: definition
of sex ratio, Fisher's principle, deviations, parthenogenetic/androgenetic species,
cyclical parthenogens, aphids, eusocial wasps/bees/ants/termites. Omit the dynamic
OWID slider images/templates (not in the pinned source section; unsupported
locally) and record the omission. Keep the excerpt's refs. Do not add a "main
article" hatnote because no verified mg target exists.""",
    ),
    "07-sex-differences": dict(
        src="source.wiki", extra="Use `supplement.wiki` for the expanded content of the source `{{excerpt|Sexual characteristics}}`; translate that sentence and its links. The section source.wiki has the rest.",
        specific="""Source lines 181-208. Headings: `== Fahasamihafana eo amin' ny lahy
sy ny vavy ==`, `=== Toetra ara-pananahana ===`, `=== Fahasamihafana ara-
pananahana ===`, `=== Fahasamihafana ara-pitondran-tena ===`. Translate the
intro (anisogamy as fundamental difference; Dawkins quotation must be translated
and clearly attributed), the sexual-characteristics excerpt sentence (from
supplement.wiki), sexual dimorphism (size/appearance, sexual selection, female
preference, stalk-eyed fly), human differences, female-larger examples, extreme
dimorphism/parasitic males, moss/liverwort examples, handicap principle, and
behavioral differences (parental care, choosiness, competition). Include images:
Male and female pheasant.jpg; Beo-2.jpg. Source Main Sexual dimorphism and See also
templates: no verified mg targets, so use plain prose/list and record. Keep all
refs, including the Dawkins quote citation.""",
    ),
    "08-see-also": dict(
        src="source.wiki", extra="No supplement.",
        specific="""Source lines 209-255. Headings: `== Jereo koa ==`,
`== Loharano ==`, `== Famakiana fanampiny ==`, `== Rohy ivelany ==`.
Translate/adapt the See also list labels (Sex allocation, Sex assignment,
Sex–gender distinction, Sexing); no verified mg targets, so keep them as plain
text with English in parentheses, not misleading links. Keep `{{reflist}}` under
Loharano. Translate the Further reading section heading and keep the five
bibliographic citations unchanged (citation metadata protected; no translated
titles). External links: omit `{{Spoken Wikipedia}}`, `{{Sister project links}}`
and the HTML comment; keep the single GFMER external link as data with a translated
label. Do not add categories. Record all template omissions.""",
    ),
}

for sid, data in sections.items():
    body = common.format(sid=sid, src=data["src"], extra=data["extra"], specific=data["specific"])
    (job / "sections" / sid / "assignment.md").write_text(body, encoding="utf-8")
    print("wrote", sid, len(body))
