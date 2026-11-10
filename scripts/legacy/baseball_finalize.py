"""Offline evidence reconciliation; review attestations remain coordinator-only."""
import re
from pathlib import Path

import mwparserfromhell as mw

from baseball_integrate import COUNTRIES, JOB, normalize_text
from mgwiki_editor.core import read_json, write_json


def main():
    text=(JOB/'draft.wiki').read_text(encoding='utf-8');code=mw.parse(text)
    records=read_json(JOB/'vocabulary.json')
    lookups={}
    allfiles=[]
    for f in sorted((JOB/'evidence').glob('lookup-*.json')):
        data=read_json(f);name=str(f.relative_to(JOB));allfiles.append(name)
        lookups[(data.get('edition'),data.get('word','').lower())]=(name,data['status'])
    write_json(JOB/'dictionary-index.json',[
        {'edition':ed,'word':word,'file':data[0],'status':data[1]}
        for (ed,word),data in lookups.items()])
    naming=['country-names.json','evidence/additional-countries-en.json',
        'evidence/additional-countries-mg.json','evidence/netherlands-local.json',
        'evidence/local-000.json','evidence/local-045.json','evidence/identity-exceptions.json']
    merged={}
    naming_terms=[]
    for rec in records:
        term=rec['source_term'];sense=rec['source_sense'];domain=rec.get('domain','')
        rec['worker_initial_reason']=rec.get('reason','')
        files=rec.get('evidence_files',[])+['dictionary-index.json','unknown-vocabulary.wiki']
        country=rec['status']=='unresolved' or any(x in term.lower() for x in
                 ['country','countries','united states','japan /','japan;','philippines','south sudan','english-born','cuban-born'])
        if country:
            # All remaining unresolved handoffs concern known country spellings,
            # not unresolved article claims. Their exact titles are now pinned.
            rec['chosen_expression']=normalize_text(rec['chosen_expression'])
            rec['malagasy_definition']=normalize_text(rec['malagasy_definition'])
            rec['status']='verified'
            rec['reason']='Coordinator resolved naming against cached country titles and pinned same-topic local pages; original source/worker notes retained. Dictionary is not naming or sovereignty authority.'
            files+=naming
            naming_terms.append(term)
        else:
            matched=[]
            for (edition,word),(filename,status) in lookups.items():
                hay=term.lower() if edition=='en' else rec['chosen_expression'].lower()
                if word and re.search(r'(?<!\w)'+re.escape(word)+r'(?!\w)',hay):
                    matched.append(filename)
            files+=matched
            rec['reason']='Coordinator compared the English source sense, editorial simple-English definition, Malagasy explanation and pinned dictionary evidence. Returned dictionary senses are candidates, not proof of established sports terminology; some Malagasy entries are garbled, unrelated or mislabeled and several lookups failed. The explicit descriptive wording, clarified by retained English where needed, resolves meaning; preferred one-word labels remain optional terminology research.'
            if rec['status']!='verified':rec['status']='descriptive'
        rec['evidence_files']=sorted(set(files))
        key=(term.lower(),sense,domain)
        if key in merged:
            old=merged[key];old['evidence_files']=sorted(set(old['evidence_files']+rec['evidence_files']))
            old.setdefault('also_sections',[]).append(rec['section_id'])
        else:merged[key]=rec
    records=list(merged.values())
    unknown=['= Voambolana mila fandinihana fanampiny =',
      'Famaritana ara-panitsiana mazava no ampiasaina ao amin’ ny lahatsoratra. Ity lisitra ity dia momba ny safidy teny ara-teknika fohy sy ny kalitaon’ ny rakibolana, fa tsy fanemorana hevitra ara-botoaty tsy fantatra. Tsy heverina ho teny efa raikitra ireo teny famaritana.']
    for rec in records:
        if rec['status']=='verified':continue
        unknown += ['\n== '+rec['source_term']+' ==',
            '* Heviny: '+rec['source_sense'],
            '* Famaritana anglisy tsotra, nataon’ ny mpandika: '+rec['english_definition'],
            '* Famaritana malagasy: '+rec['malagasy_definition'],
            '* Fomba ilazana azy: '+rec['chosen_expression'],
            '* Asa sisa: fandinihana ny teny teknika fohy raha misy porofo tsara kokoa; tsy avadika ho teny rakibolana voamarina ny teny famaritana.']
    (JOB/'unknown-vocabulary.wiki').write_text('\n'.join(unknown)+'\n',encoding='utf-8')
    records.append({'source_term':'Malagasy country naming evidence','source_language':'en',
       'domain':'geography and naming','source_sense':'Same-topic country and territory labels, not proof of sovereignty.',
       'english_definition':'Use the exact verified local page title for each geographic topic.',
       'definition_origin':'editorial_simple_english','malagasy_definition':'Ampiasaina ny lohatenin’ ny pejy malagasy voamarina fa mitovy toerana resahina.',
       'chosen_expression':'; '.join(k+' = '+v for k,v in COUNTRIES.items()),
       'status':'verified','reason':'Cache omissions resolved through actual local pages; Dominican Republic is not Dominica. England is a constituent country, not the United Kingdom. Territories are not inferred sovereign from category membership.',
       'evidence_files':naming,'alternatives_rejected':['Dôminika for Dominican Republic','Cleveland, Queensland for Cleveland, Ohio']})
    records.append({'source_term':'Read-only dictionary evidence bundle','source_language':'en','domain':'editorial evidence',
       'source_sense':'Sense checks only, not evidence for factual article claims.',
       'english_definition':'Pinned English and Malagasy lookup responses used to assess candidate word senses.',
       'definition_origin':'editorial_simple_english',
       'malagasy_definition':'Valin’ ny fikarohana voatahiry izay nampitahaina tamin’ ny hevitra tao amin’ ny loharano, fa tsy porofo momba ny zava-misy ao amin’ ny lahatsoratra.',
       'chosen_expression':'famaritana malagasy mazava arakaraka ny hevitra', 'status':'descriptive',
       'reason':'All original responses, including failures, are retained and bound. No dictionary publication endpoint called.',
       'evidence_files':allfiles+['dictionary-index.json','dictionary-review.txt','unknown-vocabulary.wiki'],
       'alternatives_rejected':['Treating malformed Malagasy entries as authoritative sports definitions']})
    write_json(JOB/'vocabulary.json',records)
    # Complete per-occurrence link inventory, including workers' pre-evidence fallbacks.
    mapping=read_json(JOB/'resolved-link-map.json');inventory=read_json(JOB/'source-link-inventory.json')
    lines=['= Fandrakofana ny rohy rehetra =']
    for n,item in enumerate(inventory,1):
        target=item['target'];base=target.partition('#')[0].replace('_',' ')
        if ':' in target:
            decision='sary/media raha File; sokajy sy metadata vahiny tsy nampidirina raha Category; rohy tetikasa rahavavy ampifanarahana ho rohy ivelany raha Wikisource'
        else:
            hit=mapping.get(base,{})
            decision=('kendrena mitovy lohahevitra '+hit['mg'] if hit.get('mg') else
                      'soratra tsotra: tsy misy kendrena malagasy mitovy lohahevitra voamarina; tsy natao rohy amin’ ny pejy tombantombana')
        lines.append(f'* {n}. <nowiki>{target}</nowiki> → {decision}.')
    (JOB/'link-coverage.wiki').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    files=read_json(JOB/'source-file-inventory.json')
    finalfiles={str(x.title).split(':',1)[1] for x in code.filter_wikilinks()
                if str(x.title).lower().startswith(('file:','image:','media:'))}
    if set(files)!=finalfiles:raise RuntimeError('Image coverage mismatch')
    filelines=['= Fandrakofana sary sy rakipeo =']
    metadata={x['title'].split(':',1)[1]:x for x in read_json(JOB/'evidence/files.json')['response']['query']['pages']}
    for name in files:
        if metadata[name].get('imagerepository')!='shared':raise RuntimeError('Not Commons: '+name)
        sections=[x['id'] for x in read_json(JOB/'section-plan.json')
                  if name in (Path(x['directory'])/'section.wiki').read_text(encoding='utf-8')]
        license_name=metadata[name].get('imageinfo',[{}])[0].get('extmetadata',{}).get('LicenseShortName',{}).get('value','')
        filelines.append('* <nowiki>'+name+'</nowiki> → '+', '.join(sections)+'; Commons; '+license_name+'. Filename tsy niova; caption/alt adika; tsy nisy sary nalaina.')
    (JOB/'file-coverage.wiki').write_text('\n'.join(filelines)+'\n',encoding='utf-8')
    # Keep the rich local source evidence bound alongside terminology and attribution.
    records=read_json(JOB/'vocabulary.json')
    records[-1]['evidence_files'] += ['link-coverage.wiki','file-coverage.wiki','section-handoffs.wiki',
        'resolved-link-map.json','reference-definitions.json','source-link-inventory.json','source-file-inventory.json',
        'evidence/files.json','evidence/categories.json','evidence/Major-League-Baseball-rosters.json',
        'evidence/Designated-hitter.json']
    records[-1]['evidence_files'] += [str(f.relative_to(JOB)) for f in sorted((JOB/'evidence').glob('links-*.json'))]
    write_json(JOB/'vocabulary.json',records)
    print('Reconciled',len(records),'records;',len(files),'Commons files;',len(inventory),'link occurrences')


if __name__=='__main__':
    main()
