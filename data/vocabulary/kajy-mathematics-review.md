# Kajy mathematics: review memory

Status: open; source issues nonblocking. Cache = candidates, not verified terms.
Source: https://kajy.blogspot.com/2011/04/ireo-voambolana-matematika-malagasy.html?m=1
Post ID: 2307042205075419731; updated 2011-04-19T08:52:08.081-07:00.
Evidence: kajy-mathematics.sqlite; source_number + table_row + source_cells_json.
Preserved import: kajy-mathematics.json. Read-only vocab tool returns decoded cells.

## KAJY-001: split expression

Rows 80/81: French `Composé (de 2 applications` / `de 2relations)`;
Malagasy expression also spans rows. Status: open.
Handling: preserve separately; flag both. Neither usable as standalone mapping
without sense review. Next: inspect both rows together; document selected wording.

## KAJY-002: numbering/layout

Number 192: empty numbered K heading; same cell contains term 193, Kisendrasendra.
Status: open. Handling: retain placeholder metadata; no invented term 192.
Section initials share cells with other first terms; source_cells retains them.
Next: use source_number, not physical table-row index, for attribution.

## KAJY-003: suspected source typos

Examples: row 82 `Congurence`; 168 `Homorphisme`; 195 `Cadimension`;
211 `Bideral`; 219 `Miromorphe`; 303 `Spectrle (valeur)`;
343 `Srjectif`; 364 `Uultrafiltra`. List illustrative, not exhaustive.
Status: open. Handling: preserve originals; no silent spelling corrections or
automatic English mappings. Next: check intended mathematical sense before use;
record corrections separately in job vocabulary reasoning, never as source quotes.

## KAJY-004: polysemy / competing mappings

Examples: Mirazotra → Colinéaire (247), Parallèle (282);
Rikitra → Symétrique (géométrie) (376), Voisinage (377);
Azo tsinjaraina → Décomposable (8), but Tsy azo tsinjaraina → Irréductible (404).
French Logarithme → Anaiso (23), Logaritima (24);
Scalaire → Kalera (204), Skalera (205); Vecteur → Tsilo, tandra, vektera (432).
Status: open; polysemy/variants not automatically errors. Handling: no global
replacement, no preferred label invented. Next: compare sense/domain and existing
article terminology; select explicitly. Record genuine source disagreement in
job source-issues.md without blocking publication for disagreement alone.

## KAJY-005: authority / rights / definitions

Source = blog wordlist; no English definitions, official-status evidence, or reuse
license verified. Status: open. Handling: terminology evidence only; no copied
article prose, claimed dictionary verification, or automatic job approval.
Next: usual sense checks + English/Malagasy definitions; pin used lookup JSON in
job vocabulary.json evidence_files. Unknown material meaning remains independent
blocker; clear descriptive wording may bypass uncertain preferred labels.
