"""Protection-aware section candidates for explicit user-supplied spellings."""
import difflib
import re
import shutil
from pathlib import Path

import mwparserfromhell as mw

from iliada_naming_plan import readable
from iliad_troasy_plan import STARTS, QUOTE
from mgwiki_editor.core import GATES, digest, now, read_json, write_json

JOB = Path('runs/iliada-naming-20261106')
MAPPING = {
    'Achilles': 'Akileosy', 'Achille': 'Akileosy', 'Hector': 'Hektôro',
    'Mycenae': 'Misenea', 'Mycènes': 'Misenea', 'Agamemnon': 'Agamemnôna',
    'Homer': 'Hômera', 'Iliasy': 'Iliada',
}
TOKEN = re.compile(r'\b(?:' + '|'.join(map(re.escape, MAPPING)) + r')\b')


def protected_ranges(text, *, lead=False, bibliography=False):
    code = mw.parse(text)
    spans = [m.span() for m in QUOTE.finditer(text)]

    def literal(value):
        spans.extend(m.span() for m in re.finditer(re.escape(value), text))

    for tag in code.filter_tags():
        kind = str(tag.tag).lower()
        if kind in {'ref', 'references', 'nowiki', 'math', 'chem'}:
            literal(str(tag))
        elif kind == 'i':
            contents = str(tag.contents)
            # The Malagasy poem title and one italic Malagasy navigation sentence
            # are not original foreign titles. All other italic runs stay intact.
            if contents == 'Iliasy' and not lead:
                continue
            if contents == 'Iliasy' and lead:
                literal(str(tag))  # The accepted lead retains this alias.
                continue
            if contents.startswith('Lahatsoratra an-tsipiriany:'):
                continue
            literal(str(tag))
    for link in code.filter_external_links():
        literal(str(link.url))
    for match in re.finditer(r'\[\[([^\]|\n]+)', text):
        spans.append(match.span(1))
    # These two appendices are bibliographic metadata; their source titles and
    # author strings are not article-name labels to rewrite.
    if bibliography:
        spans.append((0, len(text)))
    return spans


def revise(text, *, lead=False, bibliography=False):
    spans = protected_ranges(text, lead=lead, bibliography=bibliography)
    changes = []
    # Unpiped links must retain exact targets and gain an explicit display label.
    for match in re.finditer(r'\[\[([^\]|\n]+)\]\]', text):
        target = match.group(1)
        if target not in MAPPING:
            continue
        if any(a <= match.start() < b for a, b in spans):
            continue
        changes.append((match.end() - 2, match.end() - 2, '|' + MAPPING[target],
                        'explicit_label', target, MAPPING[target]))
    for match in TOKEN.finditer(text):
        if any(a <= match.start() < b for a, b in spans):
            continue
        changes.append((match.start(), match.end(), MAPPING[match.group()],
                        'visible_name', match.group(), MAPPING[match.group()]))
    result = text
    for a, b, value, *_ in sorted(changes, reverse=True):
        result = result[:a] + value + result[b:]
    audit = [{'start': a, 'end': b, 'kind': kind, 'old': old, 'new': new}
             for a, b, _, kind, old, new in sorted(changes)]
    return result, audit


def main():
    archive = JOB / 'before-user-four-names'
    archive.mkdir(exist_ok=False)
    for name in ('draft.wiki', 'vocabulary.json', 'review.json', 'resume-status.json', 'section-plan.json'):
        shutil.copyfile(JOB / name, archive / name)
    for name in ('section.wiki', 'notes.wiki', 'vocabulary.json'):
        shutil.copyfile(JOB / 'sections/00-lead' / name, archive / ('lead-' + name))
    base = (archive / 'draft.wiki').read_text(encoding='utf-8')
    positions = [0 if h is None else base.index(h + '\n') for _, h in STARTS] + [len(base)]
    assert positions == sorted(positions)
    plan = []
    for i, (sid, heading) in enumerate(STARTS):
        directory = JOB / 'sections' / sid
        fragment = base[positions[i]:positions[i + 1]]
        candidate, changes = revise(fragment, lead=sid == '00-lead',
                                    bibliography=sid in {'24-references', '25-reading'})
        for filename, content in [('resume-base.wiki', fragment), ('candidate.wiki', candidate),
                                  ('resume-base-readable.wiki', readable(fragment)),
                                  ('candidate-readable.wiki', readable(candidate))]:
            (directory / filename).write_bytes(content.encode('utf-8'))
        write_json(directory / 'candidate-diff.json', changes)
        (directory / 'candidate-changes.diff').write_text(''.join(difflib.unified_diff(
            fragment.splitlines(True), candidate.splitlines(True),
            fromfile='resume-base', tofile='proposed-user-spellings')), encoding='utf-8')
        if not changes:
            (directory / 'section.wiki').write_bytes(fragment.encode('utf-8'))
            (directory / 'notes.wiki').write_text('= Fizarana tsy ovana =\nTazonina byte-for-byte ny base; tsy misy fanoloana anarana ivelan’ ny faritra voaaro.\n', encoding='utf-8')
            write_json(directory / 'vocabulary.json', [])
        plan.append({'id': sid, 'heading': heading or 'lead/infobox',
                     'directory': str(directory), 'replacement_count': len(changes),
                     'base_sha256': digest(fragment.encode('utf-8')),
                     'status': 'pending_worker' if changes else 'unchanged_reused',
                     'dependencies': 'Shared references unchanged; exact ordered assembly; coordinator review required.'})
    assert ''.join((JOB / 'sections' / r['id'] / 'resume-base.wiki').read_text(encoding='utf-8') for r in plan) == base
    write_json(JOB / 'section-plan.json', plan)
    write_json(JOB / 'review.json', dict.fromkeys(GATES, False))
    write_json(JOB / 'user-name-map.json', MAPPING)
    (JOB / 'user-four-names.wiki').write_text("= Safidy vaovao nomen' ny mpampiasa =\nyou can use akileosy for achilles, hektôro for hector, misenea for mycene, agamemnôna for agamemnon\n\nAkileosy, Hektôro, Misenea ary Agamemnôna no ampiasaina amin’ ny prose sy captions ary headings malagasy; sora-baventy voalohany no ampiharina amin’ ny anarana manokana. Safidin’ ny mpampiasa ireo, tsy dictionary verification na fanambarana fanoratana ofisialy.\n", encoding='utf-8')
    (JOB / 'shared-context-user-names.wiki').write_text("""= Section assignment: exact narrow naming continuation =
The user has explicitly supplied Akileosy for Achilles/Achille, Hektôro for Hector, Misenea for Mycenae/Mycènes, Agamemnôna for Agamemnon. These resolve the four spelling preferences reported previously; they are user-authorized choices, NOT dictionary-verified or claimed official names. Apply these only to visible names in Malagasy prose/captions/headings and translated link labels. Preserve exact link targets; unpiped Agamemnon links gain |Agamemnôna. Continue accepted Iliada main title with Iliasy and Iliady aliases in lead, Hômera (verified local alias) for visible Homer. Troasy stays unchanged. Do NOT invent other name transcriptions. Other names already in Latin script remain unchanged in this focused continuation: no claim that every proper noun has now been respelled.
Coordinator personally read the full pinned source and sandbox and empty existing snapshot earlier in this same conversation. Source is English Iliad revision1383771922. Sandbox base is revision1153307; archived before-user-four-names/draft.wiki adds the already accepted partial lead. No source facts, contributions or references are to be lost or retranslated. Country names unchanged; pinned country-names.json is naming evidence, not sovereignty evidence.
Read YOUR resume-base.wiki and candidate.wiki fully; long lines have full soft-wrapped copies resume-base-readable.wiki and candidate-readable.wiki. Read YOUR source-en.wiki as original source context; source.wiki is the earlier local snapshot. Candidate is a coordinator's mechanical editing aid, NOT approval. Check every change, retaining exact whitespace/final-newline state. If appropriate copy candidate bytes to section.wiki; do not regenerate article prose. Report any incorrect or missed replacement to coordinator and fix only your assigned fragment, keeping changes documented.
Protect <ref>/<references>/nowiki contents, original foreign work/artwork/book/film/paper titles (including italic Agamemnon as Aeschylus's work), original quotations (including English quoted names), URLs, identifiers, Commons filenames and file options, link targets and category strings. Malagasy translated captions/glosses outside protected quotes are editable; e.g. retain italic 'Achilles Slays Hector', but change the Malagasy explanation that follows. The italic Malagasy navigation sentence in history is prose, not a foreign title, and should be harmonized. Bibliography sections24/25 are conservatively protected unchanged. Section05's heading changes Achilles to Akileosy; there are no local anchor-target changes in the candidate. Cross-section refs retain exact bytes/names/groups; full shared definitions are in ../../shared-references.wiki (job root). No new refs or templates.
Naming evidence: ../../user-four-names.wiki, ../../user-name-map.json, ../../naming-evidence/en-fr-000.json and en-fr-045.json (French identities), ../../naming-evidence/mg-name-pages.json (Hômera and Iliada local use; established local targets). User choices need no dictionary lookup; do not request one or claim evidence it did not provide. Notes/vocabulary must define source sense in simple English and Malagasy, status descriptive/user_preference for supplied names; Hômera can be locally verified. Only user-supplied targets in map may change; optional further spellings are not unresolved article facts.
Load mgwiki-style, mgwiki-edition, mg-vocab and full local manual-of-style.wiki + words-to-watch.wiki. No network, nested agents, helper detours, shared-file writes, review gates, prepare or publish. Only write section.wiki, notes.wiki, vocabulary.json in YOUR exclusive assigned directory. Coordinator alone integrates and reviews full article. Existing completed partial lead is archived; retain its approved changes. Worker completion is not final editorial approval.
""", encoding='utf-8')
    with (JOB / 'notes.wiki').open('a', encoding='utf-8') as out:
        out.write('\n== Fitohizana: anarana efatra nomen’ ny mpampiasa ==\n' +
                  'Voavaha amin’ ny safidy mazava nomen’ ny mpampiasa ireo fanoratana efatra nampiato ny asa. Tsy filazana fa lasa dictionary-verified izany. Tazonina ny partial lead nekena tao amin’ ny before-user-four-names/ ary zaraina indray ny fanitsiana manokana isam-pizarana, tsy manomboka fandikana manontolo vaovao. Scope ankehitriny: anarana efatra + fandrindrana Iliada/Hômera; tsy famoronana transcription ho anarana hafa. Tsy misy ambiguity momba ny maha izy azy na ny hevitry ny olona sy ny tanàna.\n' +
                  '\n'.join('* ' + r['id'] + ': ' + r['status'] + '; fanovana ' + str(r['replacement_count']) + '; ' + r['directory'] for r in plan) + '\n')
    print('Changed sections:', [(r['id'], r['replacement_count']) for r in plan if r['replacement_count']])
    print('Changes', sum(r['replacement_count'] for r in plan))


if __name__ == '__main__':
    main()
