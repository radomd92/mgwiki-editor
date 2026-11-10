"""Coordinator-only offline assembly; does not attest review or publish."""
import json
import re
from collections import Counter
from pathlib import Path

import mwparserfromhell as mw

from alina_native import convert

J=Path('runs/alina-iraika-20261105')


def main():
    plan=json.loads((J/'section-plan.json').read_text(encoding='utf-8'))
    fragments=[]
    section_notes=[]
    terms={}
    for row in plan:
        d=Path(row['directory'])
        for name in ('section.wiki','notes.wiki','vocabulary.json'):
            if not (d/name).is_file():
                raise RuntimeError('Missing section '+row['id']+' '+name)
        fragments.append((d/'section.wiki').read_text(encoding='utf-8').strip())
        section_notes.append('\n== '+row['id']+' ==\n'+(d/'notes.wiki').read_text(encoding='utf-8'))
        for entry in json.loads((d/'vocabulary.json').read_text(encoding='utf-8')):
            key=(entry.get('source_term','').lower(),entry.get('source_sense',''))
            entry=dict(entry)
            entry['worker_section']=row['id']
            terms.setdefault(key,entry)
    text='\n\n'.join(fragments)+'\n\n[[:Sokajy:Angano]]\n'
    (J/'assembled-before-native.wiki').write_text(text,encoding='utf-8')
    text=convert(text)
    linkmap=json.loads((J/'link-map.json').read_text(encoding='utf-8'))
    valid=set(v for v in linkmap.values() if v)
    valid.update({'Etazonia','Meksika','Aotrisy',':Sokajy:Angano'})
    code=mw.parse(text)
    fallbacks=[]
    for link in code.filter_wikilinks():
        target=str(link.title).strip()
        if target.startswith('#') or target.lower().startswith(('file:','sary:')):
            continue
        if target not in valid:
            label=str(link.text) if link.text is not None else target
            fallbacks.append((target,label))
            code.replace(link,label)
    text=str(code)
    # Standardize only new Malagasy prose, not quoted/citation strings.
    # Cross-fragment main-character spelling is a coordinator convention.
    (J/'draft.wiki').write_text(text,encoding='utf-8')
    (J/'section-notes.wiki').write_text('\n'.join(section_notes),encoding='utf-8')
    unknown='= Voambolana mila fandinihana fanampiny =\n\n'
    unknown+='Ny hevitra ampiasaina ao amin’ ny lahatsoratra dia hazavaina amin’ ny teny malagasy. Ity lisitra ity dia fitahirizana ny fisalasalana momba ny teny tokana sy ny safidy ara-piteny, fa tsy fanamarinana rakibolana na fanemorana hevitra fototra tsy voavaha.\n'
    memo=[]
    for i,entry in enumerate(terms.values(),1):
        unknown+=f"\n== {i}. {entry.get('source_term','')} ==\n"
        for field in ('source_sense','english_definition','malagasy_definition','chosen_expression','status','reason'):
            unknown+=f"* {field}: {entry.get(field,'')}\n"
        if entry.get('status')=='unresolved' or not entry.get('chosen_expression'):
            unknown+='* Tsy nampidirina tao amin’ ny lahatsoratra ilay sombin-teny simba/tsy azo hamarinina; voatahiry eto ny tsy fahalalana fa tsy navadika ho porofo.\n'
            continue
        evidence=[f"sections/{entry['worker_section']}/source.wiki",f"sections/{entry['worker_section']}/notes.wiki",'unknown-vocabulary.wiki']
        evidence.extend(['country-names.json'] if any(x in entry.get('source_term','').lower() for x in ['iran','iraq','syri','egypt','india','spain','french','mexico','austria','united states','china']) else [])
        source_term=entry.get('source_term','').lower()
        matches=[]
        for f in J.glob('lookup-*.json'):
            data=json.loads(f.read_text(encoding='utf-8'))
            if data.get('word','').lower()==source_term or (data.get('word','') and data['word'].lower() in source_term):
                matches.append(f.name)
        evidence.extend(matches)
        entry['evidence_files']=sorted(set(evidence))
        # Dictionary confirmation is not implied by local editorial definitions.
        if entry.get('status')=='verified' and not matches:
            entry['verification_scope']='local country naming only; not dictionary'
        entry.setdefault('source_language','en')
        entry.setdefault('definition_origin','editorial_simple_english')
        entry.setdefault('alternatives_rejected',[])
        memo.append(entry)
    (J/'unknown-vocabulary.wiki').write_text(unknown,encoding='utf-8')
    (J/'worker-vocabulary.json').write_text(json.dumps(memo,ensure_ascii=False,indent=2),encoding='utf-8')
    (J/'vocabulary.json').write_text(json.dumps(memo,ensure_ascii=False,indent=2),encoding='utf-8')
    audit={'sections':len(plan),'vocabulary_records':len(memo),'uncertain_items':len(terms),
           'remaining_templates':Counter(str(t.name).strip() for t in mw.parse(text).filter_templates()),
           'unverified_final_links_plaintext':fallbacks}
    (J/'assembly-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(audit,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
