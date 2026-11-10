"""Keep completed authorized omissions and actual 503 evidence; never retry a request."""
from pathlib import Path

import mwparserfromhell as mw

from earthquake_evidence import TERMS
from mgwiki_editor.core import now, read_json, write_json

JOB = Path('runs/earthquake-20261108')


def main():
    import re

    lookup_files = []
    lookups = []
    dictionary_lines = []
    for f in sorted((JOB/'evidence').glob('lookup-*.json')):
        data = read_json(f)
        rel = str(f.relative_to(JOB))
        lookup_files.append(rel)
        lookups.append((rel, data))
        dictionary_lines.append(rel+'; '+data.get('edition', '')+'; '+data.get('word', '')+'; '+data['status'])
        for entry in data.get('entries', []):
            dictionary_lines.extend('  '+d for d in entry.get('definitions', []))
    pending = []
    for english, malagasy in TERMS:
        for edition, word in [('en', english), ('mg', malagasy)]:
            filename = f'lookup-{edition}-{re.sub(r"[^a-z0-9]+", "-", english)}.json'
            if not (JOB/'evidence'/filename).exists():
                pending.append({'edition': edition, 'word': word, 'expected_output': filename})
    write_json(JOB/'evidence/resumed-overload.json', {
        'status': 'deferred_overload', 'recorded_at': now(),
        'http_status': 503, 'reported_shared_cooldown_seconds': 33,
        'error': 'Dictionary overloaded (503); shared cooldown 33s. Stop.',
        'failed_lookup': pending[0] if pending else None,
        'request_retried': False, 'write_attempted': False,
        'raw_log': 'resumed-evidence.log', 'unperformed_lookups': pending,
        'note': 'Gate exceeds ten-second waiting budget; task deferred, not manually slept or retried. This is not a dictionary miss.'
    })
    (JOB/'dictionary-review.txt').write_text('\n'.join(dictionary_lines)+'\n', encoding='utf-8')
    active = []
    omitted = []
    for rec in read_json(JOB/'vocabulary.json'):
        if 'IRIS' in rec['source_term'] or rec['source_term'] in {
            'principal stress; greatest and least principal stress', 'overburden',
            'greatest principal stress equals the weight of the rock mass'}:
            rec['coverage_status'] = 'omitted_by_user_authorization; meaning not claimed resolved'
            omitted.append(rec)
            continue
        if rec['source_term'] == 'China':
            rec.update(status='descriptive', chosen_expression='Sina, ho toerana ara-jeôgrafia tamin’ ny 1556',
                reason='Historical geographical exception, attested as short name in pinned local identity extract; do not anachronistically name the PRC in 1556.')
            rec['evidence_files'].append('evidence/local-identity.json')
        for filename, data in lookups:
            word = data.get('word', '').casefold()
            target = rec['source_term'] if data.get('edition') == 'en' else rec.get('chosen_expression', '')
            if word and word in target.casefold():
                rec['evidence_files'].append(filename)
        rec['evidence_files'] = sorted(set(rec['evidence_files']+['unknown-vocabulary.wiki', 'evidence/resumed-overload.json']))
        rec['dictionary_review_status'] = 'pinned responses retained; unfinished lookups deferred after HTTP503, not asserted complete'
        active.append(rec)
    # Preserve the deleted unresolved records outside the active proposal vocabulary.
    old_records = read_json(JOB/'before-user-authorized-omissions/vocabulary.json')
    for rec in old_records:
        if 'IRIS' in rec['source_term'] or rec['source_term'] in {
            'principal stress; greatest and least principal stress', 'overburden',
            'greatest principal stress equals the weight of the rock mass'}:
            if not any(x['source_term'] == rec['source_term'] for x in omitted):
                omitted.append(rec)
    write_json(JOB/'omitted-vocabulary.json', omitted)
    unknown = ['= Voambolana mila famerenana =',
        'Nesorina tamin’ ny dika araka ny fangatahan’ ny mpampiasa ireo filazana ara-fizika mampisalasala sy ny firesahana IRIS. Voatahiry misaraka ao amin’ ny omitted-vocabulary.json ny tsy fahazoana antoka momba ireo nesorina, fa tsy nolazaina ho voavaha. Mbola tsy vita ny lookup sy ny fanamarinana manontolo; HTTP 503 no nampiato ny fikarohana.']
    seen = set()
    for rec in active:
        key = (rec['source_term'].casefold(), rec['source_sense'])
        if key in seen:
            continue
        seen.add(key)
        unknown.extend(['\n== '+rec['source_term']+' ==',
            '* Heviny: '+rec['source_sense'],
            '* Famaritana anglisy tsotra: '+rec.get('english_definition', ''),
            '* Famaritana malagasy: '+rec.get('malagasy_definition', ''),
            '* Safidy: '+rec.get('chosen_expression', ''),
            '* Sata: '+rec['status']+'; tsy lazaina fa teny teknika efa raikitra ny teny famaritana.',
            '* Asa manaraka: mamita lookup sy famerenana voambolana rehefa azo tohizana ny asa; tsy manafoana vavahady famoahana ny lisitra.'])
    (JOB/'unknown-vocabulary.wiki').write_text('\n'.join(unknown)+'\n', encoding='utf-8')
    active.append({
        'source_term': 'User-authorized omissions and deferred evidence', 'source_language': 'en',
        'domain': 'editorial evidence', 'source_sense': 'Publication scope amended by user; remote checks deferred after service overload.',
        'english_definition': 'Problematic passages were omitted, while incomplete checks remain incomplete.',
        'definition_origin': 'editorial_simple_english',
        'malagasy_definition': 'Nesorina ireo andalana nampisalasala; tsy lazaina ho vita ny fanamarinana mbola tsy vita.',
        'chosen_expression': 'dika nohavaozina, famoahana nahemotra', 'status': 'descriptive',
        'reason': 'No override, immediate retry, external-reference access, prepare or publish after the 503.',
        'alternatives_rejected': ['Treating omitted claims as factually verified'],
        'evidence_files': lookup_files+['country-names.json', 'evidence/local-identity.json',
            'evidence/extra-links.json', 'evidence/category-search.json', 'evidence/category-membership.json',
            'evidence/resumed-overload.json', 'resumed-evidence.log', 'dictionary-review.txt',
            'unknown-vocabulary.wiki', 'omitted-vocabulary.json', 'omission-plan.json', 'section-handoffs.wiki']
    })
    write_json(JOB/'vocabulary.json', active)
    code = mw.parse((JOB/'draft.wiki').read_text(encoding='utf-8'))
    files = {str(link.title).split(':', 1)[1] for link in code.filter_wikilinks()
             if str(link.title).lower().startswith(('file:', 'image:'))}
    if files != set(read_json(JOB/'source-file-inventory.json')):
        raise RuntimeError('Image coverage changed unexpectedly')
    refs = [tag for tag in code.filter_tags() if str(tag.tag).lower() == 'ref']
    definitions = {str(t.get('name').value).strip('\"\' ') for t in refs if not t.self_closing and t.has('name')}
    if definitions != set(read_json(JOB/'reference-definitions.json'))-{'Sibson', 'Rudnicki'}:
        raise RuntimeError('Unexpected reference omission')
    with (JOB/'notes.wiki').open('a', encoding='utf-8') as f:
        f.write('\n== Fanemorana noho ny HTTP 503 ==\nVita ny fanesorana voafetra nangatahana: tsy ao amin’ ny draft.wiki intsony ny pressure–vaporization, ny fampitoviana stress–weight, na ny firesahana IRIS. Voatahiry ny fizarana 28 sy ny sary 17 ary ny famaritana references 91 tavela. Ny metadata fanampiny momba ny lohahevitra sy ny sokajy dia voapetaka; tsy nosokafana ny citation URLs.\nNijanona ny evidence worker rehefa namaly HTTP 503 ny rakibolana, niaraka tamin’ ny shared cooldown 33 segondra, izay mihoatra ny fetra fiandrasana 10 segondra. Tsy naverina ilay fangatahana ary tsy nasiana manual sleep. Tsy nisy prepare na publish natao; mbola false ny review gates satria mbola tsy vita ny famerenana sy ny preview. Ireo sakana ara-botoaty taloha dia nesorina tao amin’ ny sehatry ny dika araka ny fanomezan-dalana, fa tsy nohamarinina ara-tsiansa. Ny sata ankehitriny dia deferred_network_review, fa tsy fanekena na famoahana nahomby.\n')
    write_json(JOB/'status.json', {
        'status': 'deferred_network_review', 'updated_at': now(), 'user_authorized_omissions': True,
        'omissions_completed': ['pressure-vaporization sentence', 'stress-weight explanatory passage',
                                'IRIS related topic', 'IRIS external monitor link'],
        'previous_material_blockers_removed_from_scope': True,
        'sections_retained': 28, 'images_retained': len(files), 'reference_definitions_retained': len(definitions),
        'network_reason': 'Dictionary HTTP503; shared cooldown reported 33s; no immediate retry',
        'remaining_checks': ['complete terminology evidence/review', 'whole-article raw review',
                             'link/category coverage reconciliation', 'prepare and offline preview', 'guarded sandbox save and read-back'],
        'prepare_attempted': False, 'publish_attempted': False,
        'draft': 'draft.wiki', 'external_references_accessed': False,
    })
    print('Authorized omissions retained. Remote workflow deferred after dictionary503; no save attempted.')


if __name__ == '__main__':
    main()
