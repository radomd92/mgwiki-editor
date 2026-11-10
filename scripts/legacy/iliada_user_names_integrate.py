"""Exact coordinator integration, with no remote operations or automatic approval."""
import difflib
import re
import shutil
from collections import Counter
from pathlib import Path

import mwparserfromhell as mw

from iliada_user_names import JOB, MAPPING, protected_ranges, revise
from iliada_naming_plan import readable
from iliad_troasy_plan import QUOTE
from mgwiki_editor.core import GATES, digest, lint_wikitext, now, read_json, write_json


def signature(text):
    code = mw.parse(text)
    return {
        'references': [str(t) for t in code.filter_tags()
                       if str(t.tag).lower() in {'ref', 'references', 'nowiki'}],
        'targets': [str(link.title) for link in code.filter_wikilinks()],
        'urls': [str(link.url) for link in code.filter_external_links()],
        'quotes': QUOTE.findall(text),
        'foreign_italics': [str(t) for t in code.filter_tags()
                            if str(t.tag).lower() == 'i'
                            and str(t.contents).strip("'") not in {'Iliasy', 'Iliada'}
                            and not str(t.contents).startswith('Lahatsoratra an-tsipiriany:')],
        'categories': [str(link) for link in code.filter_wikilinks()
                       if str(link.title).startswith(':Sokajy:')],
    }


def main():
    plan = read_json(JOB / 'section-plan.json')
    state = read_json(JOB / 'job.json')
    base = (JOB / 'before-user-four-names/draft.wiki').read_text(encoding='utf-8')
    parts = []
    snippets = []
    counts = Counter()
    handoffs = []
    evidence = []
    normalization = []
    worker_vocabulary = []
    for r in plan:
        directory = Path(r['directory'])
        for filename in ('section.wiki', 'notes.wiki', 'vocabulary.json'):
            if not (directory / filename).is_file():
                raise RuntimeError('Missing handoff: ' + str(directory / filename))
        actual = (directory / 'section.wiki').read_bytes()
        candidate = (directory / 'candidate.wiki').read_bytes()
        if actual != candidate:
            assert r['id'] == '26-external' and actual == candidate + b'\n'
            normalization.append({'section': r['id'], 'only_difference': 'one extra terminal LF',
                                  'worker_sha256': digest(actual), 'accepted_sha256': digest(candidate)})
            # This is an exact, verified serialization correction, not a new prose generation.
            (directory / 'section.wiki').write_bytes(candidate)
            actual = candidate
        old = (directory / 'resume-base.wiki').read_text(encoding='utf-8')
        new = actual.decode('utf-8')
        assert signature(old) == signature(new), r['id']
        expected, changes = revise(old, lead=r['id'] == '00-lead',
                                   bibliography=r['id'] in {'24-references', '25-reading'})
        assert expected == new
        assert len(changes) == r['replacement_count']
        remaining, extra = revise(new, lead=r['id'] == '00-lead',
                                  bibliography=r['id'] in {'24-references', '25-reading'})
        assert remaining == new and not extra, r['id']
        parts.append(actual)
        r['status'] = 'accepted_by_coordinator' if changes else 'unchanged_reused_and_checked'
        r['section_sha256'] = digest(actual)
        snippets.append('== ' + r['id'] + ' ==')
        for c in changes:
            counts[c['new']] += 1
            a, b = c['start'], c['end']
            snippets.append('* ' + c['old'] + ' → ' + c['new'] + ': ' +
                            old[max(0, a - 38):a].replace('\n', ' ') + ' ⟦' +
                            old[a:b] + '⟧ ' + old[b:b + 48].replace('\n', ' '))
        handoffs.append('== ' + r['id'] + ' ==\n' + (directory / 'notes.wiki').read_text(encoding='utf-8'))
        for filename in ('resume-base.wiki', 'candidate.wiki', 'candidate-diff.json',
                         'section.wiki', 'notes.wiki', 'vocabulary.json', 'source-en-readable.wiki'):
            evidence.append(str((directory / filename).relative_to(JOB)))
        for entry in read_json(directory / 'vocabulary.json'):
            worker_vocabulary.append({'section_id': r['id'], 'record': entry})
    draft = b''.join(parts).decode('utf-8')
    assert not draft.endswith('\n')
    assert signature(base) == signature(draft)
    assert signature(state['sandbox']['text']) == signature(draft)
    assert "Ny '''''Iliada''''' na '''''Iliasy''''' na '''''Iliady'''''" in draft
    oldhead = [str(h) for h in mw.parse(state['sandbox']['text']).filter_headings()]
    newhead = [str(h) for h in mw.parse(draft).filter_headings()]
    assert newhead == [h.replace('Achilles', 'Akileosy') for h in oldhead]
    assert not any('#' in str(link.title) for link in mw.parse(draft).filter_wikilinks())
    assert not lint_wikitext(draft)
    assert sum(counts.values()) == 320
    (JOB / 'draft.wiki').write_bytes(draft.encode('utf-8'))
    (JOB / 'draft-readable.wiki').write_text(readable(draft), encoding='utf-8')
    (JOB / 'name-review-snippets.wiki').write_text('\n'.join(snippets) + '\n', encoding='utf-8')
    (JOB / 'section-handoff-notes.wiki').write_text('\n\n'.join(handoffs), encoding='utf-8')
    (JOB / 'naming-changes.diff').write_text(''.join(difflib.unified_diff(
        state['sandbox']['text'].splitlines(True), draft.splitlines(True),
        fromfile='sandbox1153307', tofile='Iliada and user-supplied four names')), encoding='utf-8')
    write_json(JOB / 'section-plan.json', plan)
    write_json(JOB / 'section-vocabulary-evidence.json', worker_vocabulary)
    write_json(JOB / 'name-change-audit.json', {
        'recorded_at': now(), 'sections': len(plan), 'name_changes_after_partial_lead': dict(counts),
        'total_after_partial_lead': sum(counts.values()), 'protected_signatures_equal': True,
        'only_heading_change': 'Achilles to Akileosy in book19–24 heading',
        'no_section_anchor_targets': True, 'serialization_normalizations': normalization,
        'sandbox_sha256': state['sandbox']['sha256'], 'draft_sha256': digest(draft.encode('utf-8')),
        'all_fragments_present': True, 'all_candidates_reviewed_by_section_workers': True,
        'final_editorial_review': 'pending coordinator raw/preview review',
    })
    previous = Path('runs/iliad-en-20261106-r1')
    for oldname, newname in [('notes.wiki', 'base-edition-notes.wiki'),
                             ('integrity-audit.json', 'base-integrity-audit.json'),
                             ('evidence/files.json', 'base-image-metadata.json'),
                             ('source-link-inventory.json', 'base-source-link-inventory.json')]:
        shutil.copyfile(previous / oldname, JOB / newname)
        evidence.append(newname)
    vocabulary = read_json(JOB / 'sections/00-lead/vocabulary.json')
    shared = ['user-four-names.wiki', 'user-name-map.json', 'user-request.wiki',
              'shared-context-user-names.wiki', 'shared-references.wiki', 'section-plan.json',
              'section-handoff-notes.wiki', 'section-vocabulary-evidence.json',
              'name-change-audit.json', 'naming-changes.diff', 'name-review-snippets.wiki',
              'country-names.json', 'link-map.json', 'source.wiki', 'sandbox.wiki', 'existing.wiki',
              'before-user-four-names/draft.wiki', 'before-user-four-names/vocabulary.json',
              'prior-proposal.json', 'prior-review.json', 'prior-receipt.json', 'prior-vocabulary.json']
    shared += [str(p.relative_to(JOB)) for p in (JOB / 'naming-evidence').glob('*.json')]
    for v in vocabulary:
        assert v['status'] in {'verified', 'descriptive'}, v['source_term']
        v['evidence_files'] = sorted(set(v['evidence_files'] + shared + evidence))
    write_json(JOB / 'vocabulary.json', vocabulary)
    write_json(JOB / 'review.json', dict.fromkeys(GATES, False))
    write_json(JOB / 'resume-status.json', {
        'status': 'integrated_pending_final_review', 'recorded_at': now(),
        'all_four_user_spelling_preferences_resolved': True, 'missing_sections': [],
        'publication_attempted': False, 'prepare_attempted': False,
        'draft_sha256': digest(draft.encode('utf-8')),
    })
    with (JOB / 'notes.wiki').open('a', encoding='utf-8') as out:
        out.write("""
== Fanakambanana voamarina: anarana efatra sy Iliada/Hômera ==
Nohamarinin' ny mpiasa mgwiki-section tsirairay ireo fizarana 25 misy fanovana; ny appendices bibliographique roa dia tazonina tsy miova. Feno ireo fragments 27, natambatra araka ny filaharana, tsy naverina nadika ny lahatsoratra iray manontolo. Fanovana anarana 320 taorian' ny partial lead nekena no voarakitra; mbola tafiditra ny fanovana 15 tao amin' ilay partial lead. Voavaha mazava ireo user preferences efatra: Akileosy, Hektôro, Misenea, Agamemnôna. Tazonina ho safidy nomen' ny mpampiasa izy ireo fa tsy porofon-dRakibolana na anarana ofisialy; tohanan' ny porofo eo an-toerana kosa ny Iliada sy Hômera. Ireo anarana hafa efa amin' ny abidy latina dia tsy novana tamin' ity fanohizana voafetra ity; tsy lazaina fa efa transcription vaovao avokoa ny anarana rehetra.
Ny fanitsiana byte tokana tamin' ny integration dia LF iray fanampiny navelan' ny fitaovana patch tao amin' ny 26-external. Efa neken' ilay mpiasa ara-kevitra ny fanovana roa rehetra, ary voaporofo fa mitovy tanteraka ny bytes sisa amin' ny candidate; nesorina ilay LF fanampiny mba hitazonana ny base tsy manana terminal LF. Tsy misy prose vaovao natsangana noho izany, ary tsy noleferina ny exact hash guard. Voarakitra ao amin' ny name-change-audit.json ireo hashes roa. Ny sakana famakiana andalana lava tao amin' ny 20-gender dia nofenoin' ny source-en-readable.wiki manontolo sy targeted follow-up; neken' ilay mpiasa ary tsy misy missing section.
Ny signatures momba ny ref/references/nowiki manontolo, original quotes, original foreign italic titles, URLs, internal link targets ary sokajy dia mitovy byte-for-byte amin' ny sandbox pinned. Tsy nisy references naverina na nanjavona; misy renderers ho an' ny groups rehetra araka ny lint. Mbola voatahiry ny sary 12 sy ny rakipeo, filenames sy options ary ireo citations rehetra. Iliada no lohatenin' ilay tononkalo amin' ny prose/captions malagasy; Iliasy sy Iliady tazonina ho anarana hafa ao amin' ny lead. Hômera no anarana hita maso ho an' i Homer, afa-tsy original titles/metadata/quotes sy appendices bibliographique voaaro. Ny anarana Agamemnon ho lohatenin' ny tantara an-tsehatra dia tsy novana. Ny teny nalaina anglisy ahitana Achilles/Agamemnon dia tsy novana. Tsy novana ny target Achille na Agamemnon; labels ihany no nampiana/nahitsy. Ny heading boky19–24 ihany no niova Achilles→Akileosy; tsy misy rohy anchor mila fanitsiana.
== Fandinihana ireo fanamarihana nolovaina ==
Nampitahain' ny mpandrindra amin' ny base-edition-notes.wiki ireo fahasamihafana source/sandbox notaterin' ny mpiasa. Efa fanapahan-kevitra editorial voarakitra taloha, fa tsy fanadinoana tamin' ity fanovana anarana ity, ny tsy fampiasana Herodotus2.116 ho porofo momba ny anaran' andriamanitra, ny tsy fampiasana ilay Fagles quote misy p589 ahiahiana sy ilay fanatsoahan-kevitra reverse-logic tsy voatohana, ny tsy famerenana ilay antsasaky ny Troiana tsy misy fanohanana, ny tsy filazana Sparta amin' ny famonoana Cassandra sy ny film1911 ho voalohany fantatra. Mijanona ny filazana voafetra sy citations efa voatahiry; tsy misy synthesis vaovao. Ny artwork1810 dia araka ny Commons metadata pinned fa tsy caption source1819, ary ny Locus2004 dia araka ny snapshot Ilium sy ref WWE-2004 efa voavaky; tsy nosokafana ireo URLs. Tsy misy olana ara-materialy vaovao tsy voavaha amin' ity naming update ity. Voatahiry eto amin' ny job ny notes/audit/image metadata/source-link-inventory taloha ho porofo pinned, ary ny sokajy roa Boky sy Angano grika dia inert, mitovy bytes sy filaharana, tsy misy vaovao nampiana.
Ny raw naming snippets sy diff ary ny draft feno efa voavaky teo aloha miaraka amin' ireo fanoloana voafetra no mbola hamaranan' ny mpandrindra ny review. Tsy fankatoavana nataon' olombelona ny handoffs; mbola false ny gates mandra-pahavitan' ny fanamarinana coordinator. Tsy mbola nisy prepare na publish tamin' ity job ity.
""")
    print('Integrated', len(plan), 'sections; changes', dict(counts))
    print('All protected signatures unchanged; review gates remain false pending coordinator review.')


if __name__ == '__main__':
    main()
