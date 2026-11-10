"""Integrate completed section handoffs; never auto-attest editorial gates."""
from pathlib import Path
from urllib.parse import unquote
import re

import mwparserfromhell as mw

from mgwiki_editor.core import read_json, write_json, lint_wikitext

J=Path('runs/achilles-20261107')


def main():
    plan=read_json(J/'corrected-section-plan.json')
    missing=[r['id'] for r in plan if any(not (Path(r['directory'])/n).is_file() for n in ['section.wiki','notes.wiki','vocabulary.json'])]
    if missing:
        raise SystemExit('Missing handoffs: '+', '.join(missing))
    fragments=[]; notes=[]; vocab=[]
    for r in plan:
        d=Path(r['directory'])
        fragment=(d/'section.wiki').read_text(encoding='utf-8')
        fragments.append(fragment.rstrip())
        notes.append(f"== {r['id']} ==\n"+(d/'notes.wiki').read_text(encoding='utf-8'))
        entries=read_json(d/'vocabulary.json')
        if isinstance(entries,dict): entries=entries.get('entries',entries.get('vocabulary',[]))
        for entry in entries:
            entry=dict(entry)
            entry['section_id']=r['id']
            evidence=[]
            for name in entry.get('evidence_files',[]):
                p=Path(name)
                if p.is_absolute() and p.is_relative_to(J.resolve()):
                    evidence.append(str(p.relative_to(J.resolve())))
                elif (J/name).is_file(): evidence.append(name)
                elif (d/name).is_file(): evidence.append(str((d/name).relative_to(J)))
            entry['evidence_files']=list(dict.fromkeys(evidence+[str((d/'notes.wiki').relative_to(J)),str((d/'source.wiki').relative_to(J))]))
            vocab.append(entry)
        r['status']='complete_pending_coordinator_review'
    draft='\n\n'.join(fragments)+'\n'
    # Source URI-encoded filename was not an existing file title. Decode to exact Commons name.
    draft=re.sub(r'(?<=File:)[^|\]\n]*%[0-9A-Fa-f]{2}[^|\]\n]*',lambda m:unquote(m[0]),draft)
    # Bibliography identifiers must not populate tracking categories in this sandbox.
    # Corrections to prose/metadata are applied separately after explicit editorial review.
    (J/'draft.wiki').write_text(draft,encoding='utf-8')
    (J/'section-handoff-notes.wiki').write_text('\n\n'.join(notes),encoding='utf-8')
    write_json(J/'section-vocabulary.json',vocab)
    write_json(J/'section-plan.json',plan)
    code=mw.parse(draft)
    links={str(x.title).split('#')[0] for x in code.filter_wikilinks()}
    mapping=read_json(J/'link-map.json')
    inventory=read_json(J/'source-link-inventory.json')
    report='= Fanamarinana ny rohy sy sary =\n'
    for target in sorted({x['target'] for x in inventory}):
        if target.lower().startswith(('file:','image:','category:')): continue
        dest=mapping.get(target.split('#')[0].replace('_',' '),{}).get('mg')
        if dest and dest in links:
            status='voatazona amin’ ny '+dest
        elif dest:
            status='TO REVIEW: verified target absent '+dest
        else:
            status='soratra tsotra voadika; tsy misy lohahevitra mg voamarina amin’ ny porofo voatahiry'
        report+=f'* {target}: {status}.\n'
    for filename in read_json(J/'source-image-inventory.json'):
        actual=unquote(filename)
        report+=f'* File:{filename}: '+('voatazona' if actual in draft else 'TO REVIEW: missing')+'; Commons metadata ao evidence/files-000.json na evidence/decoded-file.json.\n'
    (J/'coverage-audit.wiki').write_text(report,encoding='utf-8')
    refs=[t for t in code.filter_tags() if str(t.tag)=='ref']
    source=mw.parse((J/'source.wiki').read_text(encoding='utf-8'))
    source_refs=[t for t in source.filter_tags() if str(t.tag)=='ref']
    write_json(J/'structural-audit.json',dict(lint=lint_wikitext(draft),source_refs=len(source_refs),draft_refs=len(refs),templates=[str(t.name) for t in code.filter_templates()],bytes=len(draft.encode()),source_images=len(read_json(J/'source-image-inventory.json'))))
    print((J/'structural-audit.json').read_text(encoding='utf-8'))


if __name__=='__main__': main()
