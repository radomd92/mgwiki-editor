"""Offline section plan and serialized guarded metadata for Achilles."""
import shutil
from pathlib import Path

import mwparserfromhell as mw

from mgwiki_editor.core import GuardError, Wiki, now, read_json, write_json

JOB = Path('runs/achilles-20261107')
PLAN = [('00-lead',1,27),('01-etymology',28,49),('02-childhood',50,73),
 ('03-skyros',74,81),('04-war-early',82,99),('05-troilus',100,108),
 ('06-iliad',109,142),('07-penthesilea',143,151),('08-patroclus',152,157),
 ('09-death',158,170),('10-armour',171,182),('11-cult-troad',183,210),
 ('12-cult-leuce',211,230),('13-tanagra',231,246),('14-antiquity',247,272),
 ('15-literature',273,303),('16-visual',304,313),('17-music',314,330),
 ('18-screen',331,341),('19-architecture',342,353),('20-namesakes',354,358),
 ('21-gallery',359,371),('22-related',372,378),('23-bibliography',379,399),
 ('24-external',400,422)]


def local_plan():
    source = (JOB/'source.wiki').read_text()
    lines = source.splitlines(keepends=True)
    records = []
    for ident,start,end in PLAN:
        d=JOB/'sections'/ident
        d.mkdir(parents=True,exist_ok=True)
        (d/'source.wiki').write_text(''.join(lines[start-1:end]))
        records.append(dict(id=ident,start=start,end=min(end,len(lines)),directory=str(d),status='pending'))
    write_json(JOB/'section-plan.json',records)
    shutil.copyfile('data/country-names.json',JOB/'country-names.json')
    inventory=[dict(target=str(x.title),label=str(x.text or x.title)) for x in mw.parse(source).filter_wikilinks()]
    write_json(JOB/'source-link-inventory.json',inventory)
    notes="""= Fanamarihana momba ny fanitsiana =
== Fanasokajiana sy fiaviana ==
Pejy efa misy: Achille, lahatsoratra fohy tsy misy loharano, milaza ny rainy Peleus sy ny zanany Neoptolemus; mifanaraka amin' ny loharano anglisy izany ka hotehirizina. Tsy misy sandbox. Hotahirizina ny rohy Biôgrafia, Freebase sy ny sokajy sokajy:Biôgrafia (asiana colon fiarovana fotsiny). Soloina tabilao misy votoaty ny infobox foana ary esorina ny vangovango rehefa feno ny fandikan-teny.
Loharano: Wikipedia anglisy, Achilles, https://en.wikipedia.org/w/index.php?oldid=1383606011 ; mpandray anjara ao amin' ny Wikipedia anglisy, CC BY-SA 4.0. Tsy nosokafana ny rohy ivelany, DOI, boky na sary. Metadata sy soratra voatahiry ihany no nodinihina.
Ny anarana Achille dia voaporofo amin' ny existing.wiki sy ny porofo interlanguage voatahiry tamin' ny asa Iliada. Tsy ovaina ny anarana ao amin' ny lohatenin-tsanganasa sy metadata.
Tsy afindra ny navigation, maintenance, authority control sy sokajy anglisy. Ny template bibliografika manokana dia avoaka ho wikitext amin' ny API, tsy sokafana ny URL aterany. Tsy heverina ho zava-misy ara-tantara ireo angano.
== Drafitra fizarana ==
"""
    for r in records:
        notes+=f"* {r['id']}: source.wiki {r['start']}–{r['end']}; {r['directory']}; miandry. 00 mitahiry ny fianakaviana eo an-toerana; 22 sy 24 mitahiry rohy sy sokajy. 12 manohy ny lohateny ao 11; 16–19 manohy ny lohateny ao 15. Famaritana ref iombonana ao shared-references.wiki.\n"
    (JOB/'notes.wiki').write_text(notes)
    refs=[str(t) for t in mw.parse(source).filter_tags() if str(t.tag)=='ref' and t.has('name') and not t.self_closing]
    (JOB/'shared-references.wiki').write_text('\n\n'.join(refs))


def remote_evidence():
    d=JOB/'evidence'; d.mkdir(exist_ok=True)
    wiki=Wiki(); code=mw.parse((JOB/'source.wiki').read_text())
    targets={str(x.title).split('#')[0].replace('_',' ').strip() for x in code.filter_wikilinks() if ':' not in str(x.title)}
    for t in code.filter_templates():
        if str(t.name).strip().lower() in {'main','see also','ill','interlanguage link'} and t.params:
            targets.add(str(t.params[0].value).strip())
    mapping={}
    for old in [Path('runs/iliada-naming-20261106'),Path('runs/iliad-en-20261106'),Path('runs/oedipus-20261105')]:
        p=old/'link-map.json'
        if not p.exists(): continue
        for k,v in read_json(p).items():
            if k not in targets or k in mapping: continue
            src=old/v.get('evidence_file','')
            if not src.is_file(): continue
            dest=d/('reuse-'+old.name+'-'+src.name)
            if not dest.exists(): shutil.copyfile(src,dest)
            mapping[k]=dict(v,evidence_file=str(dest.relative_to(JOB)))
    remaining=sorted(targets-mapping.keys())
    for start in range(0,len(remaining),45):
        p=d/f'links-{start:03}.json'
        if not p.exists():
            data=wiki.site('en').simple_request(action='query',prop='langlinks',titles='|'.join(remaining[start:start+45]),lllang='mg',lllimit='max',formatversion=2).submit()
            write_json(p,dict(retrieved_at=now(),response=data))
        data=read_json(p)['response']
        if 'continue' in data: raise GuardError('Unprocessed link continuation')
        for page in data['query']['pages']:
            mapping[page['title']]=dict(mg=page.get('langlinks',[{}])[0].get('title'),missing=page.get('missing',False),evidence_file=str(p.relative_to(JOB)))
        for n in data['query'].get('normalized',[]):
            if n['to'] in mapping: mapping[n['from']]=mapping[n['to']]
    write_json(JOB/'link-map.json',mapping)
    files={str(x.title).split(':',1)[1].strip() for x in code.filter_wikilinks() if str(x.title).lower().startswith(('file:','image:'))}
    for t in code.filter_templates():
        for p in t.params:
            if str(p.name).strip() in {'image','image1','image2'}: files.add(str(p.value).strip())
    for tag in code.filter_tags():
        if str(tag.tag)=='gallery':
            for line in str(tag.contents).splitlines():
                if line.strip(): files.add(line.split('|')[0].split(':',1)[1].strip())
    write_json(JOB/'source-image-inventory.json',sorted(files))
    for start in range(0,len(files),45):
        p=d/f'files-{start:03}.json'
        if not p.exists():
            data=wiki.site('en').simple_request(action='query',prop='imageinfo',titles='|'.join('File:'+f for f in sorted(files)[start:start+45]),iiprop='timestamp|extmetadata',formatversion=2).submit()
            write_json(p,dict(retrieved_at=now(),response=data))
    special={'oetymd','lsj','perseus','pwre','hms','hmnzs','sclass','eb1911 poster','cite wikisource','wiktionary','commons category'}
    templates=sorted({str(t) for t in code.filter_templates() if str(t.name).strip().lower() in special})
    p=JOB/'template-expansions.json'
    if not p.exists():
        text='\n\n'.join(f'EXTRACT {i}\n{t}\nEND EXTRACT {i}' for i,t in enumerate(templates))
        data=wiki.site('en').simple_request(action='expandtemplates',title='Achilles',text=text,prop='wikitext',formatversion=2).submit()
        write_json(p,dict(inputs=templates,retrieved_at=now(),response=data))
    print('Evidence:',len(targets),'links;',len(files),'images')


if __name__=='__main__':
    local_plan()
    remote_evidence()
