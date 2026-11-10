"""Retain the completed lead, without presenting an incomplete job as reviewed."""
import re
from pathlib import Path
import mwparserfromhell as mw
from genji_en_native import native_templates, map_links
from mgwiki_editor.core import read_json, write_json, now, lint_wikitext

JOB=Path('runs/mahabharata-20261108')


def retain():
    section=JOB/'sections/00-lead'
    text=(section/'section.wiki').read_text(encoding='utf-8')
    text=native_templates(text)
    text,decisions=map_links(text,read_json(JOB/'link-map.json'))
    # Literal ISBN identifiers must not add live tracking categories.
    text=re.sub(r'(?<!>)\bISBN\s+([\dXx-]+)',r'<nowiki>ISBN \1</nowiki>',text)
    (JOB/'draft.wiki').write_text(text.rstrip()+'\n\n<references />\n',encoding='utf-8')
    entries=read_json(section/'vocabulary.json')
    for entry in entries:
        files=[]
        for f in entry.get('evidence_files',[]):
            if (section/f).is_file():
                files.append('sections/00-lead/'+f)
            elif (JOB/f).is_file():
                files.append(f)
        entry['evidence_files']=files or ['sections/00-lead/source.wiki','sections/00-lead/notes.wiki']
        entry['worker_section']='00-lead'
        term=entry.get('source_term','').lower()
        aliases={'smṛti':'smriti','puruṣārtha':'purushartha','śloka':'shloka','ślokas':'shloka',
                 'shlokas':'shloka','epic poetry':'epic','epic poem':'epic',
                 'shloka / couplet':'shloka','prose passages':'prose'}
        term=aliases.get(term,term)
        candidates={'epic':'epika','couplet':'andalana','prose':'lahatsoratra',
                    'smriti':'lovantsofina','itihasa':'tantara','dharma':'adidy',
                    'purushartha':'tanjona','shloka':'andininy'}
        checks=[]
        for edition,word in [('en',term),('mg',candidates.get(term,''))]:
            path=JOB/'evidence'/f'lookup-{edition}-{word}.json'
            if word and path.is_file():
                data=read_json(path)
                entry['evidence_files'].append(str(path.relative_to(JOB)))
                checks.append({k:data.get(k) for k in ('edition','word','status','url','retrieved_at','error','message') if k in data})
        if term=='smriti':
            entry['evidence_files'].append('evidence/lookup-en-Smriti.json')
        if checks:
            entry['dictionary_checks']=checks
            entry['reason']+=' Coordinator added the linked lookup evidence; definitions remain editorial and descriptive, not verbatim dictionary quotations.'
        elif term!='india':
            entry['dictionary_review']='not completed: article blocked before full terminology review'
    write_json(JOB/'vocabulary.json',entries)
    plan=read_json(JOB/'section-plan.json')
    for row in plan:
        row['status']='translated_pending_coordinator_review' if row['id']=='00-lead' else 'blocked_not_translated'
    write_json(JOB/'section-plan.json',plan)
    review=read_json(JOB/'review.json')
    write_json(JOB/'review.json',dict.fromkeys(review,False))
    write_json(JOB/'status.json',dict(status='blocked',updated_at=now(),
        reason='Material citation support unresolved in source lines 63–65 (named reference :0).',
        source_revision=1384087555,completed_sections=['00-lead'],
        full_translation_complete=False,prepared=False,published=False,
        retained_draft='draft.wiki',remaining_sections=31))
    with (JOB/'notes.wiki').open('a',encoding='utf-8') as out:
        out.write('''
== Vokatry ny fanamarinana sy antony nampijanonana ==
Tsy mbola feno ny fandikan-teny. Ny sasin-teny 00-lead ihany no voatahiry ho draft ampahany; tsy voamarina ho lahatsoratra feno ary tsy misy preparation na publication. Tsy tokony hatao true ny review gates satria tsy vita ny coverage sy citations.
Ny kinova anglisy 954104046 tamin' ny 30 Aprily 2020 dia efa nisy ireo filazana momba ny Abhijnanashakuntala/Urubhanga sy ny soratra varahina Sharvanatha, saingy citation needed no teo fa tsy loharano azo ampiasaina hanitsiana ref :0. Ny metadata amin' ny kinova 1384087555 dia momba ny quotas ho an' ny Marathas. Tsy hita tao amin' ny porofo Wikipedia voatahiry ny fanohanana bibliografika azo antoka ho solony. Tsy noforonina na nosoloina an-tsaina ny loharano, tsy nolazaina fa voavaky ilay URL; voasakana noho io olana citation tsy voavaha io ny fanohizana sy famoahana.
Ny lahatsoratra Ramdhari Singh Dinkar voatahiry kosa dia manondro ny Urvashi, fa tsy Rashmirathi, ho anton' ny Jnanpith tamin' ny 1972, ary mitahiry metadata momba ny lisitra Jnanpith. Voamarika io fanitsiana azo atao io ho an' ny fanohizana; tsy mbola nampidirina satria tsy vita ny fizarana 26-influence.
Ny litera simba ao amin' ny citation Gaṅgā Rām/Garg dia azo ampitahaina amin' ny kinova 2020, saingy tsy naverina nampifandraisina amin' ny filazana Punjabi vaovao: tsy midika fanamarinana citation-to-claim ny fahitana ny anarana tamin' ny kinova taloha.
Ny fizarana sisa rehetra voatahiry ho source fragments sy plan, tsy nadika, fa tsy niniana nesorina tamin' ny scope. Tsy misy pejy Wikimedia voatahiry na novaina.
== Porofon' ny sasin-teny voatahiry ==
Sary roa: Kurukshetra.jpg → infobox/tabilao sasin-teny; Krishna and Arjun on the chariot, Mahabharata, 18th-19th century, India.jpg → sary ao amin' ny sasin-teny. API imageinfo en.wikipedia: imagerepository=shared, Public domain, Copyrighted=False; tsy nalaina ny sary.
Ny template citation dia novadihana ho metadata wikitext tsotra nefa tsy nosokafana ny rohy. Ny famaritana teny dia porofo ara-piteny ihany, tsy porofo momba ny tantara. Ny epika dia tsy voamarina ho teny mg amin' ny lookup; ny teny famaritana lava no tokony ampiasaina. Ny lookup itihasa sy adidy dia tsy nahomby, fa tsy hoe tsy misy ilay teny. Ny smriti kely dia variant of Smriti fotsiny; ny lookup Smriti lehibe no manana famaritana ara-pivavahana.
''')
        out.write('\n'.join('* '+d for d in decisions)+'\n')
        out.write('\n== Tatitra worker 00-lead ==\n'+(section/'notes.wiki').read_text(encoding='utf-8'))
    errors=lint_wikitext((JOB/'draft.wiki').read_text(encoding='utf-8'))
    write_json(JOB/'partial-validation.json',dict(partial=True,valid=not errors,errors=errors,
        publication_authorized=False,reason='Incomplete translation and unresolved source citation.'))
    print('Retained partial lead; blocked, not prepared, not published.',errors)


if __name__=='__main__':
    retain()
