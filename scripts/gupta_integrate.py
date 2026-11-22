"""Normalize section evidence references; retain originals; use existing assembler."""
import json
import os
from pathlib import Path
from mgwiki_editor.workflow import assemble_sections

p=Path('runs/gupta-empire-20261122').resolve()
archive=p/'section-evidence-path-history'
archive.mkdir(exist_ok=True)
for row in json.loads((p/'section-plan.json').read_text(encoding='utf-8')):
    d=p/row['directory']
    f=d/'vocabulary.json'
    data=json.loads(f.read_text(encoding='utf-8'))
    orig=archive/(row['id']+'.json')
    if not orig.exists(): orig.write_bytes(f.read_bytes())
    records=data if isinstance(data,list) else data.get('entries',[])
    for x in records:
        result=[]
        for name in x.get('evidence_files',[]):
            if name.startswith('runs/gupta-empire-20261122/'):
                dest=p/name.split('runs/gupta-empire-20261122/',1)[1]
            elif (d/name).resolve().is_file():
                dest=(d/name).resolve()
            elif (p/name).is_file():
                dest=p/name
            else: raise ValueError((row['id'],name))
            if not dest.is_relative_to(p): raise ValueError(name)
            result.append(os.path.relpath(dest,d))
        x['evidence_files']=result
    f.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(assemble_sections(p,output=p/'assembly-v1',native_citations=True))
