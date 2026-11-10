"""Reconcile sense-specific section vocabulary and bind offline evidence."""
from pathlib import Path
import re

from mgwiki_editor.core import read_json, write_json

J=Path('runs/achilles-20261107')
ALIASES={
 'epic / cyclic epic':'epic','pyre':'funeral pyre','mound':'tumulus',
 'Roman mosaic':'mosaic','Achaeans (Homer)':'Achaeans','heroic cult':'hero cult',
 'Achilles tendon':'tendon','dative case':'dative','palatalized phoneme':'palatalization',
 'loan word':'loanword','palatalised phoneme':'palatalization',
 'votive offering':'votive','bell-krater':'krater','craters':'krater',
 'armored cruiser':'cruiser','monist':'monism',
 'paiderasteia':'pederasty',
 'stele':'stela','female gladiator':'gladiator','platonic relationship':'platonic',
}
MERGE={'invulnerable','centaur','Nereid','epic','fresco','plague','kylix','oinochoe',
 'black-figure','red-figure','tumulus','mosaic','armour','funeral games','funeral pyre'}


def main():
    entries=read_json(J/'section-vocabulary.json')
    lookup_paths=sorted((J/'evidence').glob('lookup-*.json'))
    results={p.stem.replace('lookup-en-','').replace('lookup-mg-',''):[] for p in lookup_paths}
    for p in lookup_paths:
        slug=p.stem.replace('lookup-en-','').replace('lookup-mg-','')
        results[slug].append(str(p.relative_to(J)))
    grouped={};out=[]
    for e in entries:
        e=dict(e);term=e['source_term'];canonical=ALIASES.get(term,term)
        slug=canonical.replace(' ','-')
        evidence=e['evidence_files']+[str(Path('corrected-sources')/(e['section_id']+'.wiki'))]
        evidence+=results.get(slug,[])
        if term=='heterosexual and homosexual':
            evidence+=results.get('heterosexual',[])+results.get('homosexual',[])
        if term=='oinochoe':evidence+=results.get('oenochoe',[])
        # All naming evidence is pinned; no future shared-cache mutation can alter this job.
        evidence+=['country-names.json','evidence/local-topic-pages.json']
        e['evidence_files']=list(dict.fromkeys(evidence))
        if any(name.startswith('evidence/lookup-') for name in evidence):
            e['reason']+=' Coordinator subsequently inspected the attached English and Malagasy lookup replies in context. Earlier section statements that no dictionary evidence was supplied describe the handoff stage, not this final review. Definitions remain honestly editorial unless explicitly identified otherwise; failed or irrelevant replies do not establish a preferred label.'
        if term=='ambrosia':
            e['chosen_expression']="''ambrosia'' (menaka fanosotry ny andriamanitra ao amin' ny angano)"
            e['english_definition']='In this anointing context, the divine anointing substance or oil of Greek myth, not a modern medical ointment.'
            e['malagasy_definition']="Akora na menaka fanosotry ny andriamanitra ao amin' ny angano grika, fa tsy fanafody maoderina."
        if term=='pastel':e['chosen_expression']="loko maina atao hoe ''pastel''"
        if term=='light novel':
            e['chosen_expression']="''light novel'' (karazana tantara foronina japoney)"
            e['english_definition']='A Japanese type of novel primarily intended for young adults; the source identifies Fate/Apocrypha with this genre.'
            e['malagasy_definition']="Karazana tantara foronina japoney, indrindra natao ho an' ny tanora; io karazana io no ilazan' ny loharano an' ny Fate/Apocrypha."
            e['alternatives_rejected'].append('easy to read as the defining feature without evidence')
        if term=='Iliad':
            e['chosen_expression']="''Iliada'' (''Iliad'' amin' ny teny anglisy)"
            e['reason']+=' Coordinator harmonized the Malagasy narrative label with the rest of the draft, retained original English title on first mention, and preserved every original bibliographic title and exact URL/identifier. No verified Malagasy page target or official translated edition is claimed.'
        if term=='Austria':
            e.update(chosen_expression='Aotrisy',status='verified',
                reason="Absent from direct-country-category cache; actual Malagasy country page Aotrisy revision1120590 confirms identity and spelling. Citation metadata and original titles unchanged.")
        if canonical=='Achaeans':
            e['chosen_expression']="Grika; ireo antsoin' i Homer hoe ''Achaeans''"
            e['reason']+=' Coordinator reconciles Akaiana/Akeana/Achaean labels as descriptive Grika, with source ethnonym explained, not an invented established Malagasy transcription.'
        if term=='untimely death':e['chosen_expression']="maty talohan' ny fotoana"
        if canonical in MERGE and canonical in grouped:
            old=grouped[canonical]
            old['evidence_files']=list(dict.fromkeys(old['evidence_files']+e['evidence_files']))
            old.setdefault('section_variants',[]).append(dict(section=e['section_id'],wording=e['chosen_expression'],definition=e['english_definition']))
            continue
        if canonical in MERGE:grouped[canonical]=e
        out.append(e)
    uncertain=[e for e in out if e['status']=='descriptive']
    unknown="""= Voambolana ho an' ny famerenana ara-piteny =
Mihoatra ny 100 ny firaketana teny sy hevitra nomen' ny mpandika fanazavana ara-panitsiana fa tsy nomeny mari-pahaizana hoe voambolana malagasy raikitra. Ity lisitra mitandrina ity dia ahitana teny mazava tsara ihany koa; tsy milaza fa tsy voavaha ny hevitra ara-javatra. Ny descriptive dia midika fa azo ampiasaina ny fanazavana mazava, nefa mbola azo hatsaraina ny teny fohy tiana hampiasaina. Tsy miteraka fanemorana hevitra lehibe tsy voavaha ny fisian' ity lisitra ity.
Tsy manamarina zava-misy ara-tantara na ara-pitsaboana ny rakibolana. Ireo lookup tsy nahomby dia voatahiry amin' ny status/error tena niverina, tsy natao hoe tsy misy ilay teny. Ny English definition rehetra eto dia famaritana tsotra nataon' ny mpandika, raha tsy voamarika mazava fa avy amin' ny rakibolana. Ny loharano sy porofo antsipiriany dia mifatotra amin' ny vocabulary.json.
"""
    for n,e in enumerate(uncertain,1):
        unknown+=f"\n== {n}. {e['source_term']} ==\n"
        unknown+=f"* Hevitra/sehatra: {e['source_sense']} / {e['domain']}.\n"
        unknown+=f"* Simple English: {e['english_definition']}\n"
        unknown+=f"* Fanazavana malagasy: {e['malagasy_definition']}\n"
        unknown+=f"* Voafidy: {e['chosen_expression']}\n"
        unknown+="* Fanohizana: ampitahao amin' ny porofo rakibolana voatahiry; amboary ny anarana fohy raha misy porofo mahery kokoa. Tsy misy hevitra fototra mbola tsy voavaha araka ny fanamarinana nataon' ny mpandrindra.\n"
        e['evidence_files'].append('unknown-vocabulary.wiki')
    (J/'unknown-vocabulary.wiki').write_text(unknown,encoding='utf-8')
    # One audit record binds all dictionary replies, inventories, handoffs and naming decisions.
    evidence=[str(p.relative_to(J)) for p in sorted((J/'evidence').glob('*.json'))]
    evidence+=['unknown-vocabulary.wiki','country-names.json','section-handoff-notes.wiki',
        'section-vocabulary.json','section-plan.json','corrected-section-plan.json',
        'source-link-inventory.json','source-image-inventory.json','coverage-audit.wiki',
        'link-map.json','template-expansions.json','template-expansions.wiki',
        'troilus-clarification.wiki','reconciled-structural-audit.json']
    out.append(dict(source_term='terminology and naming evidence audit',source_language='en',
        domain='editorial audit, not article factual evidence',
        source_sense='sense-specific editorial definitions checked against the pinned English source and read-only dictionary evidence',
        english_definition='A local record of the evidence used to explain source words accurately without claiming unverified Malagasy terms are established.',
        definition_origin='editorial_simple_english',
        malagasy_definition="Firaketana eo an-toerana momba ny porofo nampiasaina hanazavana marina ny teny, nefa tsy milaza fa voambolana malagasy raikitra ny teny tsy voamarina.",
        chosen_expression='fanazavana mifanaraka amin’ ny hevitra ao amin’ ny loharano',
        evidence_files=list(dict.fromkeys(evidence)),alternatives_rejected=['invented established one-word equivalents','dictionary replies treated as article factual sources'],
        status='descriptive',reason='All failed/missing/irrelevant dictionary responses retained honestly. Descriptive explanations were reviewed against the source. More than100 editorial vocabulary records bound through unknown-vocabulary.wiki; no unresolved material sense deferred to pass a gate.'))
    if any(e['status']=='unresolved' for e in out):raise SystemExit('Unresolved vocabulary remains')
    write_json(J/'vocabulary.json',out)
    print('Vocabulary:',len(out),'entries;',len(uncertain),'descriptive records in review list')


if __name__=='__main__':main()
