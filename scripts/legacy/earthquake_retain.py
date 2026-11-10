"""Preserve complete local translation without overriding unresolved factual gates."""
from pathlib import Path

import mwparserfromhell as mw

from mgwiki_editor.core import now, read_json, write_json

JOB = Path('runs/earthquake-20261108')


def main():
    text = (JOB/'draft.wiki').read_text(encoding='utf-8').replace('{{!}}', '&#124;')
    # A historical geographic label must not name the PRC as a state in 1556.
    text = text.replace("tany [[Shaanxi|Shaanxi]], any Repoblika Entim-Bahoakan' i Sina.",
                        'tany [[Shaanxi|Shaanxi]], any Sina.')
    text = text.replace("tany [[Shaanxi]], any Repoblika Entim-Bahoakan' i Sina.",
                        'tany [[Shaanxi]], any Sina.')
    (JOB/'draft.wiki').write_text(text, encoding='utf-8')
    vocab = read_json(JOB/'vocabulary.json')
    lookup_files = []
    dictionary_lines = []
    lookups = []
    for f in sorted((JOB/'evidence').glob('lookup-*.json')):
        d = read_json(f)
        rel = str(f.relative_to(JOB))
        lookup_files.append(rel)
        lookups.append((rel, d))
        dictionary_lines.append(rel+'; '+d.get('edition', '')+'; '+d.get('word', '')+'; '+d['status'])
        for entry in d.get('entries', []):
            dictionary_lines.extend('  '+value for value in entry.get('definitions', []))
    (JOB/'dictionary-review.txt').write_text('\n'.join(dictionary_lines)+'\n', encoding='utf-8')
    unknown = ['= Voambolana sy asa mbola miandry =',
               'Famaritana nataon’ ny mpandika no eto, fa tsy porofo fa teny teknika efa raikitra. Voatahiry ny valin’ ny lookup vita; natsahatra ny fikarohana fanampiny rehefa hita ny sakana ara-botoaty. Tsy vonona havoaka ny lahatsoratra.']
    seen = set()
    for rec in vocab:
        for filename, d in lookups:
            word = d.get('word', '').casefold()
            term = rec['source_term'].casefold()
            chosen = rec.get('chosen_expression', '').casefold()
            if word and ((d.get('edition') == 'en' and word in term)
                         or (d.get('edition') == 'mg' and word in chosen)):
                rec['evidence_files'].append(filename)
        rec['evidence_files'] = sorted(set(rec['evidence_files']+['unknown-vocabulary.wiki']))
        rec['dictionary_review_status'] = 'partial; see pinned evidence; no unperformed lookup represented as completed'
        if rec['source_term'] == 'China':
            rec.update(chosen_expression='Sina, ho toerana ara-jeôgrafia tamin’ ny 1556',
                       status='descriptive',
                       reason='Historical geographic exception: do not call the 1556 state the modern PRC. Sina is attested in pinned local Japàna and Himalaya extracts; modern-country full cache title retained for modern contexts.')
            rec['evidence_files'].append('evidence/local-000.json')
        key = rec['source_term'].casefold()
        if key in seen:
            continue
        seen.add(key)
        unknown.extend(['\n== '+rec['source_term']+' ==',
                        '* Heviny: '+rec['source_sense'],
                        '* Famaritana anglisy tsotra: '+rec.get('english_definition', ''),
                        '* Famaritana malagasy: '+rec.get('malagasy_definition', ''),
                        '* Safidy: '+rec.get('chosen_expression', ''),
                        '* Sata: '+rec['status']+'; mbola tsy vita avokoa ny lookup anglisy sy malagasy. Ny famaritana tsotra tsy filazana fa teny efa raikitra.',
                        '* Asa manaraka: hamita ny porofon-teny sy ny fampirindrana rehefa voavaha ny sakana ara-botoaty; tsy manafoana vavahady famoahana ity lisitra ity.'])
    (JOB/'unknown-vocabulary.wiki').write_text('\n'.join(unknown)+'\n', encoding='utf-8')
    code = mw.parse(text)
    expected_files = read_json(JOB/'source-file-inventory.json')
    actual_files = {str(x.title).split(':', 1)[1] for x in code.filter_wikilinks()
                    if str(x.title).lower().startswith(('file:', 'image:'))}
    if set(expected_files) != actual_files:
        raise RuntimeError('Image coverage mismatch')
    file_lines = ['= Fandrakofana sary =']
    metadata = {x['title'].split(':', 1)[1].casefold(): x
                for x in read_json(JOB/'evidence/files.json')['response']['query']['pages']}
    plan = read_json(JOB/'integrated-section-plan.json')
    for name in expected_files:
        meta = metadata[name.casefold()]
        license_name = meta['imageinfo'][0]['extmetadata']['LicenseShortName']['value']
        locations = [x['id'] for x in plan if name in (Path(x['directory'])/'section.wiki').read_text(encoding='utf-8')]
        file_lines.append('* <nowiki>'+name+'</nowiki>: '+', '.join(locations)+'; '+meta['imagerepository']+'; '+license_name+'; filename tsy niova; caption nadika; tsy nisy sary nalaina.')
    (JOB/'file-coverage.wiki').write_text('\n'.join(file_lines)+'\n', encoding='utf-8')
    mapping = read_json(JOB/'link-map.json')
    link_lines = ['= Fanisana rohy niandohana =',
                  'Fampitahana avy amin’ ny source inventory sy fanamarihan’ ny mpiasa; mbola tsy fanekena fa tafaverina ao amin’ ny dika ny rohy malagasy voamarina rehetra.']
    for n, item in enumerate(read_json(JOB/'source-link-inventory.json'), 1):
        target = item['target']
        base = target.split('#', 1)[0].replace('_', ' ')
        mg = mapping.get(base, {}).get('mg')
        if target.lower().startswith(('file:', 'image:')):
            decision = 'sary voatahiry, jereo file-coverage.wiki'
        elif target.lower().startswith('category:'):
            decision = 'sokajy anglisy tsy nafarana; tsy mbola misy sokajy malagasy voamarina azo ampiana'
        elif mg:
            decision = 'kendrena voamarina '+mg+'; mbola dinihina ny fandrakofana ao amin’ ny dika'
        else:
            decision = 'soratra tsotra araka ny section-handoffs.wiki; tsy misy kendrena malagasy voamarina; tsy namorona rohy'
        link_lines.append(f'* {n}. <nowiki>{target}</nowiki> → {decision}.')
    (JOB/'link-coverage.wiki').write_text('\n'.join(link_lines)+'\n', encoding='utf-8')
    refs = read_json(JOB/'reference-definitions.json')
    actual_refs = {str(t.get('name').value).strip('\"\' ') for t in code.filter_tags()
                   if str(t.tag).lower() == 'ref' and t.has('name')}
    if actual_refs != set(refs):
        raise RuntimeError('Reference name coverage mismatch')
    notes = """
== Fampidirana sy sata voasakana ==
Natambatra araka ny filaharana ny fragments 28 rehetra. Tsy misy fizarana very na novokarina indray ho lahatsoratra iray; tao amin’ ny directory manokana ihany no nanoratan’ ny mpiasa. Voatahiry ny handoffs ao amin’ ny section-handoffs.wiki. Ny dika manontolo dia draft.wiki; tsy lahatsoratra efa nekena havoaka izy io.
Voatahiry ny sary 17 rehetra, miaraka amin’ ny filename tsy niova; shared Commons avokoa araka ny metadata Wikipedia, fahazoan-dalana hita ao amin’ ny file-coverage.wiki. Tsy nisy fampidinana sary. Ireo OWID slider roa dia soloina ny sary static voasoratra ao amin’ ny loharano; tsy nafarana ny interface mihetsika tsy voamarina eto an-toerana. Tsy misy tabilao ara-botoaty very. Fanovozan-kevitra manana anarana 93 naverina avy amin’ ny famaritana loharano; citation templates navadika ho wikitext tsotra, ISBN arovan’ ny nowiki. Citation URLs, DOI sy metadata voatahiry fa tsy novakina tany amin’ ny tranonkala. Tsy natao porofo ara-botoaty ny rakibolana.
Lohateny Loharano roa nampiavahina ho Fanovozan-kevitra sy Boky sy lahatsoratra nampiasaina. Anarana Sina tamin’ ny 1556 dia toerana ara-jeôgrafia, fa tsy anaran’ ny Repoblika Entim-Bahoakan’ i Sina tamin’ izany fotoana izany; voarakitra ao amin’ ny vocabulary.json ny maningana ara-tantara. Tiorkia no nampiraisana araka ny mg langlink sy ny cache. Firenena tsy ao amin’ ny cache: Etazonia, Kanada, Meksika, Però, Filipina, Haitỳ ary Tajikistàna voaporofo amin’ ny langlinks sy local metadata voatahiry. Ny fanamarinana fandrakofana rohy farany mbola tsy vita; tsy azo asiana links_templates=true. Tsy misy sokajy malagasy voamarina tamin’ ny fangatahana voalohany, ka tsy nisy kendrena sokajy noforonina na nampiana.
Voatazona miaraka amin’ ny attribution misy daty ny tatitra samy hafa momba ny fitomboana/fihenan’ ny horohoron-tany. Tsy nesorina ny petra-kevitra momba ny tohodranon’ i Zipingpu; voatazona ny tsy mbola naha-voaporofo tanteraka azy. Ny elanelan’ ny isan’ ny maty tany Tangshan ao amin’ ny vatana no nampiraisana tamin’ ny sasin-teny. Fanavahana angovo/magnitioda sy halalin’ ny foibe/teboka ambonin’ ny tany nohatsaraina tamin’ ny porofo anatiny; ireo fiovana voafaritra ao amin’ ny handoffs dia tsy porofo avy amin’ ny external reference.

== Sakana ara-botoaty tsy azo foanana amin’ ny autonomous mode ==
Ao amin’ ny source andalana 108 sy 07-rupture dia lazaina fa ny fiakaran’ ny tsindrin’ ny tsiranoka no mahatonga ny fitomboan’ ny fivadihan’ ny rano ho etona. Tsy voavaha ny fahamarinan’ io rohy ara-antony io: tsy ampy ny citation metadata mba hanamarinana na hanitsiana ny filazana ara-fizika. Voatazona ao amin’ ny dika ilay filazana araka ny fangatahan’ ny mpampiasa hitazona ny text mampiady hevitra; tsy navadika ho fanekena ny fahamarinany izany. Tsy nosokafana ireo URL ivelany, tsy noforonina fanitsiana na fanambarana fa efa novakina ny references.
Ao amin’ ny 03-faults koa, ny fampitovian’ ny source ny stress sy weight dia novolavolaina ho fihenjanana ateraky ny lanja mba tsy hampitovy refy samy hafa, nefa mbola mila fanamarinana ara-botoaty izany interpretation izany. Tsy noterena ho verified ilay rakitra unresolved. Tsy ampy porofo ny fanitarana IRIS ao amin’ ny appendices; tsy noforonina izany.
Natsahatra an-tsitrapo ny evidence worker rehefa fantatra ireo sakana; exited 143, fa tsy overload na dictionary miss. Ny lookup vita rehetra voatahiry, ary ny dictionary-review.txt manavaka found/failed; tsy lazaina ho vita ny lookup mbola tsy natao. Nisy memo entries 256 tamin’ ny merge (227 source_term samihafa, anisan’ izany anarana sy fanafohezana); unknown-vocabulary.wiki natomboka ho an’ ny fanaraha-maso teny ara-teknika, tsy isa manamarina hevitra tsy fantatra.
Tsy nisy prepare, preview MediaWiki na publish natao. Mbola false ny editorial gates rehetra; lint structural fotsiny no nandalo, tsy fanamarinana ara-piteny na ara-tsiansa. Tsy misy proposal digest, receipt, human approval na on-wiki save. Voatahiry ny dika sy ny porofo rehetra eto amin’ ny job.
"""
    with (JOB/'notes.wiki').open('a', encoding='utf-8') as f:
        f.write(notes)
    for item in plan:
        item['status'] = 'fragment_complete; article_blocked_pending_coordinator_review'
    write_json(JOB/'integrated-section-plan.json', plan)
    vocab.append({
        'source_term': 'Pinned naming and editorial evidence bundle', 'source_language': 'en',
        'domain': 'editorial evidence', 'source_sense': 'Local snapshots, partial lookups and metadata; not final publication approval.',
        'english_definition': 'Evidence retained for a blocked draft; unfinished checks remain unfinished.',
        'definition_origin': 'editorial_simple_english',
        'malagasy_definition': 'Porofo voatahiry ho an’ ny dika mbola voasakana; tsy lazaina ho vita ny fanamarinana mbola tsy natao.',
        'chosen_expression': 'dika eo an-toerana mbola tsy nekena havoaka', 'status': 'descriptive',
        'reason': 'Unresolved scientific citation interpretation blocks publication; requested controversial passages retained in local draft.',
        'alternatives_rejected': ['Treating autonomous mode as permission to override citation or meaning gates'],
        'evidence_files': lookup_files + ['country-names.json', 'title-evidence.json',
            'dictionary-review.txt', 'unknown-vocabulary.wiki', 'file-coverage.wiki',
            'link-coverage.wiki', 'section-handoffs.wiki', 'reference-definitions.json',
            'evidence/files.json', 'evidence/categories.json', 'evidence/local-000.json']
    })
    write_json(JOB/'vocabulary.json', vocab)
    write_json(JOB/'status.json', {
        'status': 'blocked_content_verification', 'recorded_at': now(),
        'draft': 'draft.wiki', 'sections_retained': len(plan), 'images_retained': len(expected_files),
        'reference_definitions_retained': len(refs), 'publish_attempted': False,
        'blockers': ['Unresolved pressure-vaporization causal claim, source line108',
                     'Stress/weight interpretation requires factual review',
                     'IRIS acronym expansion not evidenced',
                     'Terminology and whole-article link review unfinished'],
        'user_requested_controversial_text_retained': True,
        'external_references_accessed': False,
        'dictionary_worker': 'stopped intentionally after identifying factual blocker; exit143'
    })
    print('Retained complete draft; publication blocked. Sections', len(plan), 'images', len(expected_files), 'references', len(refs))


if __name__ == '__main__':
    main()
