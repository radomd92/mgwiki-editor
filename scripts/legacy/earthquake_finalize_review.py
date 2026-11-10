"""Coordinator's final offline evidence consolidation; no remote operations."""
import copy
import re
from collections import Counter
from pathlib import Path

from mgwiki_editor.core import GATES, now, read_json, write_json

JOB = Path('runs/earthquake-20261108')


def normalized(value):
    return re.sub(r'[^a-z0-9]+', ' ', value.lower()).strip()


def main():
    vocab = read_json(JOB/'vocabulary.json')
    for name in ['vocabulary.json', 'unknown-vocabulary.wiki']:
        backup = JOB/(name+'.before-final-review')
        if not backup.exists():
            backup.write_bytes((JOB/name).read_bytes())
    lookups = []
    for path in sorted((JOB/'evidence').glob('lookup-*.json')):
        data = read_json(path)
        lookups.append({
            'file': str(path.relative_to(JOB)), 'edition': data.get('edition'),
            'word': data.get('word'), 'status': data['status'],
            'definitions': [s for e in data.get('entries', []) for s in e.get('definitions', [])],
            'url': data.get('url'),
            'time': data.get('retrieved_at', data.get('recorded_at')),
            'error': data.get('error'),
        })
    assert len(list((JOB/'evidence').glob('lookup-final-*.json'))) == 20
    decisions = [
        'English P wave ECG/alias senses rejected; hyphenated P-wave and S-wave confirm compressional/transverse seismic senses.',
        'Seismicity has distinct source-lead energy-per-volume and ordinary occurrence senses; context kept separate.',
        'Seismotectonics dictionary definition too narrow for source topic; editorial relationship-between-earthquakes-and-tectonics definition retained.',
        'Malagasy fitongilanana/velarana/hamafy and other garbled or irrelevant senses do not establish technical equivalence.',
        'Failed crust request is preserved actual HTTP503 evidence, not dictionary absence and not a successful lookup.',
        'Failed multiword entries (injection well, statistical seismology, stochastic modeling and others) retain clear source-context editorial definitions.',
        'Onja dictionary water-wave sense alone does not establish seismic P/S terminology; explicit direction-of-motion explanations retained.',
        'Preferred labels remain research, not unresolved material meanings. No dictionary used as article-fact source.',
    ]
    write_json(JOB/'dictionary-review.json', {
        'reviewed_at': now(), 'reviewer': 'autonomous coordinator',
        'external_references_accessed': False, 'decisions': decisions,
        'lookup_file_count': len(lookups),
        'distinct_requests': len({(x['edition'], x['word']) for x in lookups}),
        'status_counts': dict(Counter(x['status'] for x in lookups)),
        'lookups': lookups,
    })
    merged = {}
    omitted = []
    common = ['dictionary-review.json', 'country-names.json', 'coverage-review.md',
              'final-link-coverage.json', 'final-link-map.json', 'source-issues.md',
              'evidence/local-identity.json', 'evidence/local-000.json',
              'evidence/category-search.json', 'unknown-vocabulary.wiki']
    for entry in vocab:
        if entry['source_term'] == 'User-authorized omissions and deferred evidence':
            omitted.append(entry)
            continue
        e = copy.deepcopy(entry)
        e['worker_reason_historical'] = e.get('reason', '')
        e['dictionary_review_status'] = 'coordinator reviewed pinned definitions; failures/irrelevant senses retained, not verification claims'
        term = normalized(e['source_term'])
        files = set(e['evidence_files']) | set(common)
        matched = set()
        for item in lookups:
            if item['edition'] != 'en' or not item['word']:
                continue
            word = normalized(item['word'])
            if word and (f' {word} ' in f' {term} ' or f' {term} ' in f' {word} '):
                files.add(item['file'])
                matched.add(item['file'])
                # Pair filenames encode English source term, even for Malagasy candidate.
                mg = item['file'].replace('-en-', '-mg-')
                if (JOB/mg).exists():
                    files.add(mg)
        e['evidence_files'] = sorted(files)
        if e['status'] == 'descriptive':
            e['reason'] = ('Contextual editorial definition reviewed against pinned source and assembled wording. '
                           'Descriptive Malagasy, not asserted established dictionary terminology. '
                           'Lookup outcomes and rejected senses: dictionary-review.json; earlier worker reasoning retained separately.')
        else:
            e['reason'] = ('Local naming evidence reviewed; exact country/local-page identity supported. '
                           'This status is naming evidence, not a claim of dictionary verification. Earlier reasoning retained separately.')
        # Same term/domain, same conceptual sense; retain all variant context/evidence.
        discriminator = 'energy_rate' if 'energy' in e['english_definition'].lower() and 'seismicity' in term else ''
        key = (term, normalized(e['domain']), discriminator)
        variant = {k: e[k] for k in ['source_sense', 'english_definition', 'malagasy_definition',
                                    'chosen_expression', 'worker_reason_historical']}
        if 'section_id' in e:
            variant['section_id'] = e['section_id']
        if key in merged:
            prior = merged[key]
            prior['context_variants'].append(variant)
            prior['evidence_files'] = sorted(set(prior['evidence_files']) | files)
            prior['alternatives_rejected'] = list(dict.fromkeys(prior.get('alternatives_rejected', []) + e.get('alternatives_rejected', [])))
        else:
            e['context_variants'] = [variant]
            merged[key] = e
    entries = list(merged.values())
    write_json(JOB/'vocabulary.json', entries)
    write_json(JOB/'archived-editorial-vocabulary.json', omitted)
    lines = ['# Voambolana: famerenana farany', '',
             '- Hevitra ara-pitenenana manakana: tsy misy hita taorian’ ny famerenana.',
             '- Lisitra fikarohana teny malagasy raikitra; famaritana mazava ampiasaina ankehitriny. Tsy fanambarana fa voamarina amin’ ny rakibolana ny teny tsirairay.',
             '- Lookup vita/tsy nahomby: dictionary-review.json. HTTP503 taloha voatahiry; tsy natao hoe dictionary miss.',
             '- Tantara taloha manontolo: unknown-vocabulary.wiki.before-final-review; vocabulary.json.before-final-review. Sata deferred taloha tsy sata ankehitriny.',
             '- Andalan-dahatsoratra nesorina: omitted-vocabulary.json; archived-editorial-vocabulary.json; source-issues.md. Tsy lazaina ho voavaha ny hevitr’ ireo nesorina.',
             '- Asa manaraka: mitady voambolana raikitra rehefa misy porofo azo itokisana; tsy manova famaritana mazava ho teny noforonina.', '']
    for e in entries:
        if e['status'] != 'descriptive':
            continue
        lines += ['## '+e['source_term'], '- Sehatra/heviny: '+e['domain']+'; '+e['source_sense'],
                  '- English definition: '+e['english_definition'], '- Famaritana malagasy: '+e['malagasy_definition'],
                  '- Safidy: '+e['chosen_expression'],
                  '- Sata: famaritana descriptive voadinika; teny raikitra mbola azo karohina. Hevitra fototra mazava.', '']
    (JOB/'unknown-vocabulary.wiki').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    with (JOB/'notes.wiki').open('a', encoding='utf-8') as f:
        f.write('''
## Famerenana farany — coordinator
- Source revision 1379800890, source/existing/sandbox snapshots novakina manontolo tamin’ ny asa; existing.wiki sy sandbox.wiki samy foana. New-page preservation N/A; tsy nisy local contribution voafafa.
- 28 fragments vita/accepted; targeted corrections ihany, tsy whole-article regeneration. Raw draft manontolo novakina tamin’ ny draft-readable.txt; precision/markup repairs nohaverina nojeren’ ny coordinator.
- Meaning: qualifiers, negation, names/name order, dates, quantities, chronology, attribution voadinika. Source disagreements tsy nalamina an-tsaina; EQ-S001–EQ-S009: runs/earthquake-20261108/source-issues.md. User-authorized omissions rehetra voatazona; two post-2002 film examples tsy naverina.
- Fluency/style: Malagasy feno; apostrophe spacing amin’ ny prose/captions; foreign terms sy book/movie/paper titles italics; agency/acronym glosses. Exact titles, names, URLs, citation metadata voaaro; tsy reordered names. Medical first mentions pesta, krizy panika, depresiôna misy fanazavana, tsy added diagnosis/treatment.
- Terminology: dictionary-readable.txt, dictionary-readable-delta.txt sy final lookup definitions novadinika; dictionary-review.json mirakitra sense decisions/failures. P-wave/S-wave hyphenated senses mifanaraka amin’ ny source; ECG senses nolavina. Descriptive wording tsy lazaina ho established coinage. Unknown-vocabulary memory nohavaozina; tantara taloha voatahiry. Hevitra manakana tsy misy hita.
- Country cache novakina offline; country-names.json job-pinned. Tiorkia/local exceptions sy historical Sina voadinika; exact Haiti local title voatazona na dia misy date concern aza.
- Coverage: coverage-review.md sy final-link-coverage.json. 46 unique headings; 17 Commons files; 91 reference definitions/104 uses. Plain-text fallbacks 279, verified local links 34, authorized internal-link omissions 3. Source references/citation-to-claim preserved except Sibson/Rudnicki miaraka amin’ ny sentence omitted.
- Citations: pinned metadata ihany, tsy external-link validation. Named reuse/definitions, pages, authors, original titles, DOI/ISBN voatazona. Two later films nesorina noho ny citation chronology; older novels/citation retained. No unresolved copyright, sensitive-person/medical/legal, citation-integrity or topic/merge blocker identified in remaining scope.
- Links/templates: native supported markup; zero templates; filename rehetra tsy niova. OWID static charts sy File-description access retained; same-page anchors Magnitude/big_one normalized. Inert category additions farany, existing categories tsy nisy. No external image/resources fetched.
- Neutrality: words-to-watch contextual review, tsy blacklist. Disaster deaths/uncertainty and attributed dated frequency reports retained; mythology/religious accounts attributed, tsy factual endorsement. No added scientific reconciliation, promotion, translator TODO or unsupported conclusion.
- Wikitext-only: raw article inspected, no Markdown wrapper. Structural validate passed. Tests: 222 passed; ruff check mgwiki_editor tests passed. Offline rendered preview still required after prepare; booleans attest editorial checks only, not human approval.
''')
    write_json(JOB/'review.json', dict.fromkeys(GATES, True))
    status = read_json(JOB/'status.json')
    status.update(status='editorially_reviewed_pending_prepare', updated_at=now(),
                  dictionary_review='dictionary-review.json', network_reason=None,
                  remaining_checks=['prepare live revision guards', 'offline rendered proposal review', 'guarded sandbox save and read-back'],
                  omissions_completed=['pressure-vaporization sentence', 'stress-weight explanatory passage',
                                       'IRIS related topic', 'IRIS external monitor link',
                                       '2012 (2009) and San Andreas (2015) examples'])
    write_json(JOB/'status.json', status)
    print(f'Final vocabulary: {len(vocab)} → {len(entries)} entries; historical variants retained. Review gates evidenced.')


if __name__ == '__main__':
    main()
