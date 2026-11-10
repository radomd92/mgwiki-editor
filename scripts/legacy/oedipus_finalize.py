"""Coordinator integration and evidence memo; no automatic review attestations."""
import json
import re
from pathlib import Path
from urllib.parse import quote

JOB = Path('runs/oedipus-20261105')


def main():
    text = (JOB / 'draft.wiki').read_text(encoding='utf-8')
    changes = {
        "''Oidípous'' amin' ny teny grika taloha": "Oidípous amin' ny teny grika taloha",
        "Mahery fo manana fiafarana mampalahelo (''tragic hero'')":
            "Mahery fo manana fahalemena mitarika azy ho amin' ny fahalavoana (''tragic hero'')",
        "ilay antsoiny hoe ''Oedipus complex'', izany hoe faniriana tsy tsapan' ny zaza lahy mba ho azy irery ny fitiavan' ny reniny":
            "ilay fitambaran' ny faniriana tsy tsapa mitondra ny anarany (na fanirian' ny zaza lahy mba ho azy irery ny fitiavan' ny reniny; ''Oedipus complex'')",
        "fetin' i Dionysia": "fety Dionysia",
        "tamin' ny ''City Dionysia''": "tamin' ny fifaninanana tao amin' ny fety ''City Dionysia''",
        "i Athens": "i Atena",
        "avy any Corinth": "avy any Kôrinto",
        "mpanjakan' i Corinth": "mpanjakan' i Kôrinto",
        "Achaeus of Eretria": "Achaeus avy any Eretria",
        'taor. J.K.': "taorian' i Kristy",
        "talohan' i Jesoa Kristy": "talohan' i Kristy",
        "[[Seneka Zandriny|Seneca the Younger]]": "[[Seneka Zandriny|Seneca zandriny]]",
        "E.F. Watling's Introduction to ''Seneca: Four Tragedies and Octavia''":
            "Sava lalana nosoratan' i E.F. Watling ho an' ny ''Seneca: Four Tragedies and Octavia''",
        "i Antigone sy i Ismene, izay feno ranomaso ny masony": "i Antigone sy i Ismene, tao anatin' ny ranomaso",
        'see: "': 'Jereo: "',
        '(often reprinted) – the 1994 Loeb, however, prints Sophocles in chronological order.':
            "(navoaka indray imbetsaka); ao amin' ny fanontana Loeb tamin' ny 1994 kosa dia araka ny filaharana ara-potoana ny sanganasan' i Sophocles.",
        '; see also F. Jouan': '; jereo koa F. Jouan',
        'Reviewed by Hugh Lloyd-Jones in "Gnomon"': "Nodinihin' i Hugh Lloyd-Jones tao amin' ny ''Gnomon''",
        "Harpers Dictionary of Classical Antiquities (1898)": "''Harpers Dictionary of Classical Antiquities'' (1898)",
        'Wilson, Christopher. "Oedipus: The message in the myth", The Open University':
            "Wilson, Christopher. ''Oedipus: The message in the myth'', The Open University",
    }
    applied = []
    for old, new in changes.items():
        if old in text:
            text = text.replace(old, new)
            applied.append((old, new))
    # Native title formatting inside literal bibliographic references, not URLs.
    text = text.replace('R. Kannicht, Tragicorum Graecorum Fragmenta (TrGF)',
                        "R. Kannicht, ''Tragicorum Graecorum Fragmenta'' (TrGF)")
    text = text.replace('"Euripide. tome 8.2 – Fragments"', "''Euripide. tome 8.2 – Fragments''")
    text = text.replace('Euripides, Phoenissae 35–38', "Euripides, ''Phoenissae'' 35–38")
    text = text.replace('Homer, Odyssey 11.271–280', "Homer, ''Odyssey'' 11.271–280")
    text = text.replace('in "Museum Helveticum"', "ao amin' ny ''Museum Helveticum''")
    text = text.replace('== Tetiarana ==', "== Tetiarana ==\n<!-- Ny tetiarana dia fampifanarahana avy amin’ ny mpandray anjara ao amin’ ny Wikipedia anglisy: https://en.wikipedia.org/w/index.php?oldid=1371034526 ; CC BY-SA 4.0. -->")
    audio = "[[File:LL-Q1860 (eng)-Naomi Persephone Amethyst (NaomiAmethyst)-Oedipus.wav|Fanononana ny anarana anglisy hoe Oedipus]]"
    text = text.replace("ao anatin' ny tontolo tsy miantra.\n", "ao anatin' ny tontolo tsy miantra. "+audio+'\n')
    (JOB / 'draft.wiki').write_text(text, encoding='utf-8')
    entries = json.loads((JOB / 'section-vocabulary.json').read_text(encoding='utf-8'))
    aliases = {
        'oracle at delphi': 'oracle', 'incestuous marriage': 'incest', 'incestual love': 'incest',
        'hubristic': 'hubris', 'adoptive': 'adoption', 'neck amphora / red-figure': 'amphora',
        'regency': 'regent',
        'plague / pestilence': 'plague', 'expose / exposure': 'exposure',
        'spurious ending': 'spurious',
    }
    lookup_index = {}
    for f in (JOB / 'evidence').glob('lookup-*.json'):
        match = re.fullmatch(r'lookup-(en|mg)-(.+)\.json', f.name)
        edition, key = match.groups()
        lookup_index[(edition, key.lower())] = f
    for entry in entries:
        key = entry['source_term'].lower()
        key = aliases.get(key, key).replace(' ', '-')
        metadata = []
        for edition in ['en', 'mg']:
            f = lookup_index.get((edition, key))
            if f is None:
                continue
            relative = str(f.relative_to(JOB))
            if relative not in entry['evidence_files']:
                entry['evidence_files'].append(relative)
            data = json.loads(f.read_text(encoding='utf-8'))
            word = data.get('word', '')
            metadata.append({'edition': edition, 'word': word,
                             'url': data.get('url') or 'http://192.168.1.155:8000/wiktionary-pages/'+edition+'/'+quote(word, safe=''),
                             'retrieved_at': data.get('retrieved_at'), 'status': data.get('status')})
        if metadata:
            entry['lookup_metadata'] = metadata
            entry['reason'] += ' Coordinator inspected the attached lookup definitions in context; dictionary candidate misses, unrelated senses and failures do not verify the chosen compound. Clear descriptive wording is retained.'
        if entry['source_term'] == 'tragic hero':
            entry['chosen_expression'] = "mahery fo manana fahalemena mitarika azy ho amin' ny fahalavoana (''tragic hero'')"
        if entry['source_term'] == 'Oedipus complex':
            entry['chosen_expression'] = "fitambaran' ny faniriana tsy tsapa mitondra ny anaran' i Œdipe (''Oedipus complex'')"
    # Deduplicate only identical sense records; preserve sense distinctions.
    unique = {}
    for entry in entries:
        key = (entry['source_term'].lower(), entry['source_sense'])
        if key not in unique:
            unique[key] = entry
        else:
            existing = unique[key]
            existing['evidence_files'] = sorted(set(existing['evidence_files'] + entry['evidence_files']))
    entries = list(unique.values())
    entries.append({
        'source_term': 'Oedipus / naming and edition evidence', 'source_language': 'en',
        'domain': 'proper naming and editorial provenance',
        'source_sense': 'The mythic Greek king represented by existing Malagasy Œdipe; country and city labels, inherited categories and licensed illustrations.',
        'english_definition': 'The locally evidenced name and contextual naming evidence for this translation.',
        'definition_origin': 'editorial_simple_english',
        'malagasy_definition': "Anarana voaporofo sy antontan-kevitra ampiasaina hitazonana ny lohahevitra sy ny tsipelina amin' ny fandikan-teny.",
        'chosen_expression': 'Œdipe; Atena; Grisia Taloha; Kôrinto', 'status': 'descriptive',
        'alternatives_rejected': ['unverified Malagasy proper-name coinages'],
        'reason': 'Source en→mg link and existing snapshot confirm topic; targeted supplemental langlinks confirm Atena and Grisia Taloha. Country cache is naming-only, not sovereignty evidence. Source contemporary United States wording is expressed adjectivally as amerikanina; Nigeria appears only in protected citation metadata. No external link was consulted.',
        'evidence_files': ['country-names.json', 'link-map.json', 'source-link-inventory.json',
                           'section-plan.json', 'shared-context.wiki', 'section-notes.wiki',
                           'section-vocabulary.json', 'evidence/files.json', 'evidence/local-categories.json',
                           'evidence/family-template.json', 'evidence/family-template.wiki',
                           'evidence/related-evidence.json', 'evidence/local-topic-evidence.json',
                           'evidence/rotimi-evidence.json', 'evidence/chart-code-evidence.json',
                           'evidence/implicit-links-audio.json']
    })
    (JOB / 'vocabulary.json').write_text(json.dumps(entries, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    with (JOB / 'notes.wiki').open('a', encoding='utf-8') as f:
        f.write('\n== Fampiraisana nataon’ ny mpandrindra ==\n')
        f.write('Ny section-notes.wiki dia mitahiry ny handoff rehetra; ny sakana tranainy voavaha dia vakina miaraka amin’ ny fanitsiana farany. Tsy faneken’ olona ny fanamarinana mandeha ho azy.\n')
        f.write('Ny sarintanin’ ny rohy sy ny notes isaky ny fizarana dia manazava ny kendrena rehetra sy ny soratra tsotra ampiasaina rehefa tsy voamarina ny pejy mg. Tsy filazana fa tsy misy pejy mg ny mg=null. Sary enina: samy Commons/shared sy fahazoan-dalana malalaka araka ny evidence/files.json, tsy nisy nalaina ny sary. Ny rakipeo anglisy dia nampidirin’ ny mpandrindra indray rehefa voamarina ho shared/CC BY-SA 4.0 tao evidence/implicit-links-audio.json; tsy manan-kery intsony ny fanilihana vonjimaika ao 00-lead/notes.wiki. Ny anaran-drakipeo dia tsy niova, ao amin’ ny faran’ ny fehintsoratra voalohany. Tsy nalaina ny feo.\n')
        f.write('Ny rohy avy amin’ ny citation author1-link, author2-link sy ill dia nojerena manokana: Antti Aarne, Stith Thompson ary Walter Puchner dia tsy manana kendrena mg voamarina ao evidence/implicit-links-audio.json, ka notazonina ho anaran’ ny mpanoratra tsy misy rohy, fa tsy noforonina pejy.\n')
        f.write('Ny Eteocles mpanjaka nandimby ao amin’ ny tabilao voalohany sy Creon mpisolo mpanjaka ao amin’ ny tabilao farany dia avahana araka ny fanasokajian’ ny tetiarana; tsy namoronana faharetana na daty. Ny fehezanteny mikorontana momba ny ranomaso ao Oedipus Rex dia soratana tsy manendry hoe iza marina no nitomany. Ny Oidípous dia anaran’ olona fa tsy teny vahiny tokony hatao sora-mandry.\n')
        f.write('Voatahiry ny rohy [[Biôgrafia]] sy Freebase. Ny sokajy efa nisy dia [[:sokajy:Biôgrafia]], ny teboka roa voalohany ihany no nampiana ho fiarovana; ampiana any amin’ ny farany [[:Sokajy:Angano grika]], izay pejy voamarina. Tsy afindra ny sokajy anglisy.\n')
        f.write(f'Voambolana: {len(entries)} firaketana misy hevitra voafaritra; latsaky ny 101 ny teny anglisy mampisalasala samy hafa. Ny teny mahazatra voazava mazava dia fitadidiana ara-panoratana, fa tsy lazaina ho valin’ ny rakibolana. Tsy misy hevitra manan-danja mbola tsy voavaha.\n')
        for old, new in applied:
            f.write('* Fampiraisana: '+old+' → '+new+'\n')
    print('Integrated memo:', len(entries), 'records; no review gates set')


if __name__ == '__main__':
    main()
