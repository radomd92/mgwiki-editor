"""Coordinator reconciliation of sense-specific memos and pinned lookup evidence."""
from pathlib import Path
import re
import unicodedata
from mahabharata_terms import PAIRS, slug
from mgwiki_editor.core import read_json, write_json

JOB=Path('runs/mahabharata-20261108')


def norm(s):
    s=unicodedata.normalize('NFD',s.casefold())
    s=''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+',' ',s).strip()


GROUPS={
 'critical edition':('Critical Edition','textual criticism'),
 'india':('India','country naming'), 'itihasa':('itihasa','Hindu textual classification'),
 'swayamvara':('swayamvara','marriage ceremony in the epic'),
 'interpolation':('interpolation','textual criticism'),
 'later interpolation':('interpolation','textual criticism'),
 'svarga':('svarga','Hindu narrative afterlife'), 'swarga':('svarga','Hindu narrative afterlife'),
 'parvas':('parva','structure of the Mahabharata'), 'parva sub parva':('parva','structure of the Mahabharata'),
 'volumes':('volume','bibliographic structure'), 'volume':('volume','bibliographic structure'),
 'prose passages':('prose','literary form'),
 'dharmayuddha just war':('dharmayuddha / just war','ethics of war'),
}
ALIASES={
 'smrti':'smriti', 'slokas shloka':'shloka', 'sloka':'shloka',
 'story within a story frametales':'frame story', 'frametales':'frame story',
 'compositional layers':'compositional layers', 'lifelong celibacy':'celibacy',
 'fraternal polyandry':'polyandry',
 'massive conglomerate company':'conglomerate', 'liberation moksa jainism':'moksha',
 'canon canonical literature':'canon', 'chivalrous notions of warfare dishonorable tactics':'chivalry',
 'possessed by the spirits':'possession',
}


if __name__=='__main__':
    records=read_json(JOB/'merged-worker-vocabulary.json')
    merged={}
    for e in records:
        term=norm(e['source_term'])
        key=GROUPS.get(term,(e['source_term'],e['domain']))
        if key in merged:
            old=merged[key]
            old['evidence_files']=sorted(set(old['evidence_files']+e['evidence_files']))
            old['worker_sections']=sorted(set(old['worker_sections']+[e['worker_section']]))
            old.setdefault('section_expressions',[]).append(e['chosen_expression'])
        else:
            merged[key]=dict(e,source_term=key[0],domain=key[1],worker_sections=[e['worker_section']])
    entries=list(merged.values())
    for e in entries:
        term=norm(e['source_term']); search=' '+term+' '+ALIASES.get(term,'')+' '
        checks=[]
        for en,mg in PAIRS+[('epic','epika'),('couplet','andalana'),('prose','lahatsoratra'),
                              ('smriti','lovantsofina'),('itihasa','tantara'),('dharma','adidy'),
                              ('purushartha','tanjona'),('shloka','andininy')]:
            n=norm(en)
            if not re.search(r'\b'+re.escape(n)+r'\b',search): continue
            for edition,word in [('en',en),('mg',mg)]:
                path=JOB/'evidence'/f'lookup-{edition}-{slug(word)}.json'
                if not path.is_file(): continue
                data=read_json(path)
                e['evidence_files'].append(str(path.relative_to(JOB)))
                checks.append({k:data.get(k) for k in ['edition','word','status','url','retrieved_at','error','message'] if k in data})
        if term in {'jaundiced','jaundice'}:
            for name in ['lookup-en-jaundice.json','lookup-mg-'+slug('jôndisy')+'.json']:
                p=JOB/'evidence'/name
                if p.is_file(): e['evidence_files'].append(str(p.relative_to(JOB)))
        extras={'smrti':['lookup-en-Smriti.json'],'kshatriya':['lookup-en-kshatriya-full.json'],
                'shastra':['lookup-en-Shastra-full.json'],'archaeoastronomy':['lookup-en-archaeastronomy-full.json'],
                'painted grey ware':['lookup-en-ware.json','lookup-mg-fitaovana.json']}
        for n,files in extras.items():
            if n in term:
                for name in files:
                    p=JOB/'evidence'/name
                    if p.is_file(): e['evidence_files'].append(str(p.relative_to(JOB)))
        e['evidence_files']=sorted(set(e['evidence_files']))
        e['dictionary_checks']=checks
        if 'painted grey ware' in term:
            e['chosen_expression']="zavatra vita amin' ny tanimanga volondavenona misy hosodoko (PGW; Painted Grey Ware)"
            e['reason']+=' Coordinator clarified ware as pottery objects, not raw clay; Malagasy fitaovana lookup is only a broad candidate, not an established term for the pottery culture.'
        if term=='kavya':
            e['chosen_expression']="tononkalo (''kāvya'')"
        if term=='shastra':
            e['chosen_expression']="soratra fampianarana (''shastra'')"
        if term=='theatrical adaptation':
            e['english_definition']='Here, a planned adaptation for performance. The ambiguous medium label is not retained as a claim specifically about stage theatre.'
            e['malagasy_definition']="Eto dia tetikasa fampifanarahana hoentina amin' ny fampisehoana; tsy faritana ho teatra an-tsehatra ilay medium manjavozavo."
            e['chosen_expression']="fampifanarahana nokasain' i Satyajit Ray"
            e['reason']+=' Coordinator omitted the ambiguous medium adjective rather than guessing stage versus screen; the planned project and citation remain.'
        e['coordinator_review']='Source sense and descriptive Malagasy wording compared against the pinned source and assembled article. Dictionary matches are lexical evidence only; weak or failed lookups are not treated as established Malagasy equivalents.'
        if e['status'] not in {'verified','descriptive'}:
            raise ValueError('Unresolved vocabulary: '+e['source_term'])
        if e['definition_origin']!='editorial_simple_english':
            # Workers may use another honest origin; do not manufacture dictionary quotations.
            e['definition_origin_review']='Retained worker-labelled origin; see evidence.'
    entries.append(dict(source_term='Singapore',source_language='en',domain='country naming exception',
        source_sense='Country/city-state where Krishna Udayasankar is based',
        english_definition='The country and city-state called Singapore.',definition_origin='editorial_simple_english',
        malagasy_definition='Ilay firenena sady tanàna atao hoe Singaporo.',chosen_expression='Singaporo',
        evidence_files=['country-names.json','evidence/reused-country-exceptions.json'],
        alternatives_rejected=[],status='verified',reason='Absent from the direct country category cache; verified local page title Singaporo and same-topic lead, revision1149935.'))
    evidence_files=['source.wiki','existing.wiki','sandbox.wiki','shared-references.wiki',
                    'worker-contract.wiki','resume-context.wiki','section-plan.json',
                    'worker-notes.wiki','source-link-inventory.json','source-image-inventory.json',
                    'source-to-draft-link-coverage.json','coverage-report.json','link-decisions.json',
                    'final-link-map.json','link-map.json','template-conversion-inventory.json',
                    'terminology-request-index.json']
    evidence_files += [str(p.relative_to(JOB)) for p in (JOB/'evidence').glob('*.json')]
    evidence_files += [str(p.relative_to(JOB)) for p in (JOB/'sections').glob('*/section.wiki')]
    entries.append(dict(source_term='Mahabharata',source_language='en',domain='topic identity and edition provenance',
        source_sense='The requested epic, its illustrations and same-topic linked pages in this translation.',
        english_definition='The epic translated here, with the pinned evidence used to identify its title, illustrations and links.',
        definition_origin='editorial_simple_english',
        malagasy_definition="Ilay tononkalo fitantarana adika eto, miaraka amin' ny porofo voatahiry momba ny lohateny, sary sy rohy.",
        chosen_expression='Mahabharata',evidence_files=sorted(set(evidence_files)),
        alternatives_rejected=['Unverified local link targets and unverified category names'],status='verified',
        reason='Proper-name/topic and editorial-evidence record, not a dictionary-derived factual claim or invented equivalent. Binds all used naming, image, link and section evidence to the proposal.'))
    uncertain=[]; seen=set()
    for e in entries:
        if e['status']=='verified': continue
        key=norm(e['source_term'])
        if key in seen: continue
        seen.add(key); uncertain.append(e)
    out='''= Voambolana hohamarinina amin' ny fanoratana tiana kokoa =
Lisitra fitahirizana ara-piteny ity, fa tsy lisitry ny hevitra ara-tantara tsy voavaha. Voafaritra araka ny source ny hevitra rehetra nampiasaina; mbola azo hatsaraina amin' ny fanamarinana voambolana ny teny tokana tiana kokoa. Ampidirina amim-pitandremana koa ireo fanazavana tsotra sy original terms rehefa tsy misy label mg tokana voamarina. Tsy rakibolana manamarina article facts ity ary tsy mamorona teny efa ekena. Ny famaritana anglisy sy malagasy eto dia editorial_simple_english raha tsy voalaza mazava ho hafa ao amin' ny vocabulary.json.
'''
    for e in uncertain:
        out+='\n== '+e['source_term']+' ==\n'
        out+='* Sehatra sy hevitra: '+e['domain']+'; '+e['source_sense']+'\n'
        out+='* Simple English: '+e['english_definition']+'\n'
        out+='* Fanazavana malagasy: '+e['malagasy_definition']+'\n'
        out+='* Teny nampiasaina: '+e['chosen_expression']+'\n'
        out+='* Tsy fahazoana antoka: label malagasy fohy na fanoratana mahazatra ihany; tsy dikany manan-danja tsy voavaha. Dingana manaraka: fanamarinana voambolana manokana raha ilaina; tsy manolo ny fanazavana marina efa nampiasaina.\n'
        e['evidence_files']=sorted(set(e['evidence_files']+['unknown-vocabulary.wiki']))
    (JOB/'unknown-vocabulary.wiki').write_text(out,encoding='utf-8')
    write_json(JOB/'vocabulary.json',entries)
    write_json(JOB/'vocabulary-reconciliation.json',dict(worker_records=len(records),merged_records=len(entries),
        distinct_descriptive_labels=len(uncertain),unresolved_material_meanings=[],
        unknown_list='unknown-vocabulary.wiki',policy='Conservative list started above 100 records; known contextual meanings are not represented as unknown facts.'))
    print('Reconciled',len(records),'records into',len(entries),'; descriptive labels',len(uncertain))
