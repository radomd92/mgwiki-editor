---
name: mgwiki-style
description: Required Malagasy encyclopedia style and strict MediaWiki output rules for article translation
---

# Malagasy encyclopedia style guide

Apply to every mgwiki-editor translation. This is the project's editorial
baseline, not a claim to be an official Malagasy Wikipedia community policy.
Read `references/manual-of-style.wiki` and `references/words-to-watch.wiki` in
full before drafting or reviewing. They integrate the two user-requested English
Wikipedia guides into this Malagasy baseline, with source revision attribution.
Use these local references, not per-article web fetches. Explicit project rules
below override incompatible English-language conventions; preserve verifiability,
quotation fidelity, and confirmed local policy. Never invent community consensus,
official translations, name components, or local template names.

## Mandatory Malagasy conventions

- In newly written Malagasy prose, separate an elision apostrophe from the next
  word with one space: `amin'ny` becomes `amin' ny`; `an'Andriamanitra` becomes
  `an' Andriamanitra`; `amin'izao` becomes `amin' izao`. Apply the same convention
  to other Malagasy apostrophized forms, including `tamin' ny` and `ho an' ny`.
  This is a project spelling convention, not English possessive grammar. Do not
  run a global apostrophe replacement: preserve foreign names such as O'Connor,
  quotations, original titles, citation metadata, identifiers, URLs, code, and
  MediaWiki's paired/triple apostrophes for italics/bold. Link labels may be
  adapted; exact link targets and template parameter names must not be rewritten.
- Foreign-language acronyms/abbreviations may retain their original letters and
  established punctuation. On first mention add their accurate Malagasy
  translation or expansion in parentheses, including common acronyms; repeat
  in a self-contained caption/table when needed. Example: `WHO (Fikambanana
  Iraisam-pirenena momba ny Fahasalamana)`. Do not invent a Malagasy acronym or
  mistake an explanatory translation for an official institutional name.
- Italicize retained foreign-language words/phrases with `''teny vahiny''`;
  keep a foreign term inside parentheses italicized too. Established Malagasy
  equivalents and Malagasy explanatory translations stay roman. Acronym tokens
  and personal/place names stay in their established form, not italic solely
  because of foreign origin. Retained full foreign agency/institution names get
  a Malagasy translation in parentheses; as foreign-language phrases, italicize
  the full name, not its Malagasy gloss. Keep names accurate and distinguish
  explanatory translations from verified official Malagasy names.
- Preserve original/culturally established order for all personal names; never
  mechanically Westernize or reverse them. Chinese, Japanese, Korean, and
  Vietnamese names explicitly retain their original order, including in
  romanization. Specific Malagasy convention: surname first, given names last
  when the components are verified. This is the explicit local exception if a
  source has Westernized the order. Never guess a surname from the last token,
  split a mononym, or reorder uncertain components. Preserve source spelling and
  name order verbatim inside quotations, original work titles, and citation
  metadata; document uncertain identity/name structure outside the article.
- Italicize mentioned book, movie/film, and paper/research-article titles using
  MediaWiki paired apostrophes, including short paper titles that English MoS
  would normally put in quotation marks. This is an explicit project override.
  Keep the exact title wording/language and original internal word order. Do not
  insert formatting into URLs, identifiers, or literal citation-template title
  fields: use supported rendering, avoiding double italics. Quoted source text
  stays faithful; do not reformat the whole quotation as a work title.
- Words to watch are caution signals, never a forbidden-word list. Review the
  Malagasy equivalents for the same bias, vagueness, unsupported implications,
  and imprecision as the English examples. Prefer sourced facts and attribution.
  Do not replace/censor such words inside citations, original titles, or direct
  quotations. Those exceptions protect faithful reproduction, not endorsement
  of a source's viewpoint in the article's own voice; translated quotations must
  be labelled and preserve the source's meaning and tone.

## Language and fidelity

- Write fluent, complete standard Malagasy sentences. Use natural Malagasy
  information order and verbal voice, not English/French word-for-word syntax.
- Use neutral encyclopedic register, third person, clear transitions, and concise
  explanations. No conversational asides, promotional language, or caveman prose.
- Preserve qualifications, uncertainty, negation, chronology, attribution,
  numerical precision, and distinctions among causation, association, and opinion.
- Lead with a clear definition of the topic; bold its Malagasy name at first
  mention with triple apostrophes. Lead summarizes the supported body.
- Prefer established Malagasy terminology. Explain unfamiliar concepts on first
  use. Where necessary give the original technical term in parentheses after a
  clear Malagasy explanation, without implying a coined word is standard.
- For an unfamiliar term, first write a simple context-specific English
  definition in the vocabulary memo, then translate its meaning into Malagasy.
  A clear descriptive expression is acceptable without a confirmed one-word
  equivalent; record editorial definitions honestly, not as dictionary evidence.
- For medical terms use `[Malagasy transcription] (na [Malagasy explanation])`
  on first mention, optionally adding the English term in parentheses. Use
  `asma` for asthma. Explain the condition simply without adding unsupported
  medical claims about the subject or inventing an established spelling.
- Resolve ambiguity by sense and subject domain, not surface resemblance. Check
  both dictionary editions for non-trivial vocabulary. Dictionary misses do not
  prove that a word is wrong; machine-generated definitions may themselves err.
  A failed lookup can be recorded while a clear editorial definition is used;
  genuinely unresolved material meanings still stop the publication gate. Follow
  mg-vocab's unknown-vocabulary.wiki procedure above 100 distinct uncertain items.
- Keep names, taxonomic binomials, formulae, official titles, quoted originals,
  identifiers, and bibliographic titles accurate. Translate descriptive prose,
  captions, and headings; never fabricate Malagasy forms of proper names.
- Normalize country names in new Malagasy prose/captions to the matching exact
  page titles cached from mg.wikipedia's `Sokajy:Firenena` in
  `data/country-names.json`. Use `python3 -m mgwiki_editor countries` (offline
  cache read); populate once or explicitly update with `countries --refresh`.
  Do not refetch the category for each article. Category membership is not a
  complete list of countries or proof of sovereignty: it includes generic pages
  and may omit countries categorized elsewhere. Check topic identity before
  using a title; if absent or ambiguous, record verified local-page evidence
  rather than inventing a match or repeatedly refreshing the category. Preserve
  originals in quotations, bibliographic titles, identifiers and URLs. Pin the
  naming evidence in the job through vocabulary.json evidence_files.
- Use consistent spelling, apostrophes, contractions, and terminology. Preserve
  Malagasy diacritics where used, normalize Unicode consistently, and avoid
  gratuitous capitalization. Apply the Malagasy elision spacing above to new
  prose only. Do not mechanically replace punctuation in URLs, identifiers,
  mathematical expressions, or quotations.
- Dates, quantities, units, coordinates, and tables retain their exact meaning;
  adapt readable date phrasing consistently without ambiguous numeric dates.
  Do not convert measurements without keeping verified equivalence.

## Wikipedia editing

- Translate supported claims, not a source article's vandalism or obvious errors.
  Check questionable claims, especially living-person, medical, and legal claims.
  Flag unresolved problems outside the article and stop the publication gate.
- Preserve citations at the claims they support, named references and reuse,
  bibliography, URLs, DOI/ISBN identifiers, page numbers, and access dates.
  Citation metadata keeps original titles; translations may supplement them only
  through verified supported fields. Never claim to have read an inaccessible
  reference. Never invent a reference or use dictionary entries as factual proof.
- Do not open citation URLs or external-links entries, or launch general web
  searches, by default; do not ask permission just to do so. Preserve references
  from the pinned source and state which checks were not performed. An explicit
  user request may authorize external research. This does not prohibit required
  Pywikibot CLI reads/previews or read-only dictionary lookups. If a material
  factual conflict cannot be resolved, flag it rather than browsing around the
  restriction or pretending it was verified.
- Translate internal link labels; resolve Malagasy targets via actual pages or
  interlanguage links. Do not create plausible-looking links to wrong topics.
  Plain unlinked text is better than a wrong link; record unresolved targets.
- Do not copy foreign templates blindly. Verify local template and parameter
  support. Prefer native wikitext or a simpler verified equivalent if absent;
  do not silently lose scientific data, references, or accessibility information.
- Keep Commons filenames unchanged. Translate captions/alt descriptions. Verify
  locally hosted/non-free images separately; foreign-local files may not exist
  or be reusable on mg.wikipedia.org.
- Preserve sourced Malagasy contributions in existing articles. No unsupported
  synthesis, removal of inconvenient claims, or unreviewed full replacement.
- Add relevant Malagasy category links (Sokajy) at the end of the article, after
  all sections and appendices. Preserve existing Malagasy article/sandbox category
  links: do not translate, rename, remove, reorder, or duplicate them; retain their
  targets, labels, and sort keys. Do not guess targets or blindly import foreign
  categories. Already-inert links remain byte-for-byte unchanged; adding a leading
  colon to an existing live link is the sole sandbox-safety exception.
- Keep sandbox categories inert using [[:Sokajy:Name]] (or colon-prefixed source
  category links for review). Record additions and safety-only changes in notes.wiki.
  Avoid live category membership, interwiki language
  links, DEFAULTSORT, redirects, and templates that categorize the sandbox.
  Do not edit Wikidata; save proposed metadata in local notes instead.
- Plain ISBN magic links can add tracking categories on mgwiki even without any
  template. Preserve literal bibliography identifiers using, for example,
  `<nowiki>ISBN 0-393-97141-4</nowiki>` when needed to prevent that side effect;
  check the rendered result and never disable the no-categories guard.

## Wikitext only

- Article artifact: UTF-8 draft.wiki, containing only page wikitext.
- Sections: == Tantara == and === Zana-pizarana ===; never ATX headings.
- Bold: '''teny'''; italics: ''teny''; never asterisks for emphasis.
- Internal links: [[Pejy|soratra]]; external links: [https://example.org soratra].
- Lists: MediaWiki * and # lists are legitimate. Do not mistake them for Markdown
  merely because Markdown shares those characters. No task-list boxes.
- Tables: {| class="wikitable", |-, ! headings, | cells, |}; not pipe tables.
- References: <ref name="anarana">…</ref>, <ref name="anarana" />, and
  <references /> (including matching groups where needed).
- Never use code fences, backticks, Markdown links, Markdown image syntax,
  Markdown emphasis, Markdown horizontal rules, or prose wrappers.
- Structural lint is only a gate: some syntaxes overlap, and a parser cannot
  prove the absence of all Markdown or the quality of Malagasy. Inspect raw
  wikitext and the offline rendered preview before publishing.
