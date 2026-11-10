"""Offline section plan and shared evidence compilation; no remote calls."""
import json
import re
import shutil
from pathlib import Path

import mwparserfromhell as mw

J = Path('runs/alina-iraika-20261105')


def main():
    source = (J/'source.wiki').read_text(encoding='utf-8')
    mapping, aliases = {}, {}
    for f in sorted(J.glob('links-*.json')):
        data = json.loads(f.read_text(encoding='utf-8'))['query']
        for row in data.get('normalized', [])+data.get('redirects', []):
            aliases[row['from']] = row['to']
        for row in data['pages']:
            mapping[row['title']] = row.get('langlinks', [{}])[0].get('title')
    for name in aliases:
        target = aliases[name]
        seen = {name}
        while target in aliases and target not in seen:
            seen.add(target)
            target = aliases[target]
        mapping[name] = mapping.get(target)
    (J/'link-map.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
    images = {}
    for f in J.glob('images-*.json'):
        for row in json.loads(f.read_text(encoding='utf-8'))['query']['pages']:
            images[row['title']] = {'repository':row.get('imagerepository'), 'license':row.get('imageinfo',[{}])[0].get('extmetadata',{}).get('LicenseShortName',{}).get('value')}
    (J/'image-map.json').write_text(json.dumps(images,ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.copyfile('data/country-names.json',J/'country-names.json')
    starts = [(m.start(),m.group()) for m in re.finditer(r'^={2,4}[^\n]*={2,4}\s*$',source,re.M)]
    groups = [
      ('01-lead',0,'==Synopsis==','Teny fampidirana'),
      ('02-synopsis','==Synopsis==','==History, versions and translations==','Famintinana'),
      ('03-history','==History, versions and translations==','===Possible Indian influence===','Tantara sy dika ary fandikan-teny'),
      ('04-indian','===Possible Indian influence===','===Persian prototype:','Mety ho fiantraikan’ ny literatiora indiana'),
      ('05-persian','===Persian prototype:','===Evolving Arabic manuscripts===','Ny fototra persiana: Hezār Afsān'),
      ('06-manuscripts','===Evolving Arabic manuscripts===','=== Printed Arabic editions ===','Ny fivoaran’ ny sora-tanana arabo'),
      ('07-printed','=== Printed Arabic editions ===','===Modern translations===','Fanontana arabo natao pirinty'),
      ('08-translations','===Modern translations===','===Timeline===','Fandikan-teny maoderina'),
      ('09-timeline','===Timeline===','==Literary themes and techniques==','Filaharan’ ny zava-nitranga'),
      ('10-frame','==Literary themes and techniques==','===Embedded narrative===','Lohahevitra sy fomba fitantarana; tantara mandrafitra'),
      ('11-embedded','===Embedded narrative===','===Dramatic visualization===','Tantara ao anatin’ ny tantara'),
      ('12-visual','===Dramatic visualization===','===Fate and destiny===','Famaritana mampahita ny zava-mitranga'),
      ('13-fate','===Fate and destiny===','===Foreshadowing===','Anjara sy lahatra'),
      ('14-foreshadow','===Foreshadowing===','===Repetition===','Fambara mialoha'),
      ('15-repetition','===Repetition===','===Sexual humour===','Famerimberenana'),
      ('16-humour','===Sexual humour===','===Unreliable narrator===','Vazivazy ara-nofo'),
      ('17-narrator','===Unreliable narrator===','=== Genre elements ===','Mpitantara tsy azo itokisana'),
      ('18-crime','=== Genre elements ===','{{Anchor|Horror fiction elements}}','Toetoetran’ ny karazana literatiora: tantara heloka bevava'),
      ('19-horror','{{Anchor|Horror fiction elements}}','{{Anchor|Fantasy and science fiction elements}}','Tantara mampihorohoro'),
      ('20-fantasy','{{Anchor|Fantasy and science fiction elements}}','===Poetry===','Tantara mahagaga sy tantara foronina ara-tsiansa'),
      ('21-poetry','===Poetry===','==In world culture==','Tononkalo'),
      ('22-culture','==In world culture==','===In Arab culture===','Eo amin’ ny kolontsaina maneran-tany'),
      ('23-arab','===In Arab culture===','{{Anchor|Possible early influence on European literature}}','Eo amin’ ny kolontsaina arabo'),
      ('24-early','{{Anchor|Possible early influence on European literature}}','{{Anchor|Western literature from the 18th century onwards}}','Literatiora eoropeana tany aloha'),
      ('25-galland','{{Anchor|Western literature from the 18th century onwards}}','==== 19th century–20th century ====','Literatiora tandrefana; fandikan-tenin’ i Galland'),
      ('26-western','==== 19th century–20th century ====','{{Anchor|Cinema and television}}','Taonjato faha-19 sy faha-20'),
      ('27-film','{{Anchor|Cinema and television}}','===Music===','Sarimihetsika sy radio ary fahitalavitra'),
      ('28-music','===Music===','===Theatre===','Mozika'),
      ('29-theatre','===Theatre===','===Games===','Teatra'),
      ('30-games','===Games===','===Illustrators===','Lalao'),
      ('31-illustrators','===Illustrators===','===Comic books===','Mpanao sary'),
      ('32-comics','===Comic books===','==Gallery==','Tantara an-tsary'),
      ('33-gallery','==Gallery==','==See also==','Sary'),
      ('34-related','==See also==','== References ==','Jereo koa'),
      ('35-references','== References ==','==Further reading==','Loharano sy fanovozan-kevitra'),
      ('36-reading','==Further reading==','==External links==','Boky azo vakina'),
      ('37-external','==External links==','{{One Thousand and One Nights|state=expanded}}','Rohy ivelany'),
    ]
    plan=[]
    for ident,a,b,heading in groups:
        start = a if isinstance(a,int) else source.index(a)
        end = source.index(b)
        d=J/'sections'/ident
        d.mkdir(parents=True,exist_ok=True)
        (d/'source.wiki').write_text(source[start:end],encoding='utf-8')
        plan.append(dict(id=ident,source_start=start,source_end=end,heading=heading,directory=str(d),status='pending',dependencies=[]))
    (J/'section-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    # Full reference definitions are shared, so earlier fragments may keep reuses.
    refs=[]
    for tag in mw.parse(source).filter_tags():
        if str(tag.tag)=='ref' and not tag.self_closing and tag.has('name'):
            refs.append(str(tag))
    (J/'shared-references.wiki').write_text('\n\n'.join(refs),encoding='utf-8')
    notes='= Fanamarihana momba ny fanitsiana =\n\n'
    notes+='== Fanasokajiana sy fiaviana ==\nLahatsoratra vaovao: samy foana ny pejy malagasy sy ny toerana fitsapana voatahiry. Tsy manana rohy mg ny loharano araka ny fangatahana API voafetra tamin’ ny teny mg. Ny lohateny nomen’ ny mpampiasa no ampiasaina.\n'
    notes+='Loharano: [https://en.wikipedia.org/w/index.php?oldid=1383561034 One Thousand and One Nights, revision 1383561034], Wikipedia contributors, CC BY-SA. Tsy novakina ny rohy ivelany. Voatahiry tsy novana ny metadata sy ny lahatsoratra loharano.\n'
    notes+='== Drafitra isam-pizarana ==\n'
    for row in plan:
        notes+=f"* {row['id']}: {row['heading']}; elanelan-tsoratra {row['source_start']}–{row['source_end']}; {row['directory']}; miandry. Tsy misy soratra malagasy teo aloha; miankina amin’ ny fampiraisana references sy voambolana.\n"
    notes+='== Fanapahan-kevitra momba ny loharano ==\n'
    notes+='* Ny fampidirana dia milaza «Iranian Golden Age», nefa ny famaritana manontolo milaza fanangonana naharitra taonjato maro tany amin’ ny faritra samihafa. Tsy halaina ilay fanondroana vanim-potoana mifanohitra amin’ izany; hotazonina ny filazana voaporofo hoe fanangonana natao nandritra ny taonjato maro.\n'
    notes+='* Tsy hampiasaina ho porofo ny rohy truyen audio full izay tsy mifandray amin’ ny fandikan-tenin’ i Lyons; hotazonina ny loharano Buchan sy ny hafa mifanandrify. Tsy nitsidika ilay rohy ny mpandrindra.\n'
    notes+='* Tsy hafindra ny môdely fitetezana sy fitantanana anglisy, DEFAULTSORT ary ny sokajy anglisy. Ny rohy sokajy malagasy ihany no ho ampiana raha voamarina.\n'
    notes+='== Sarintany rohy ==\n'
    for target,mg in sorted(mapping.items()):
        notes+=f'* {target} → '+(mg+' (rohy mitovy lohahevitra voamarina amin’ ny langlinks).\n' if mg else 'soratra tsotra; tsy misy rohy mg voamarina tamin’ ny API, tsy noforonina ny tanjona.\n')
    notes+='== Tahiry sary ==\n'
    for target,row in sorted(images.items()):
        notes+=f"* {target}: {row['repository']}; {row['license']}; toerana ao amin’ ny fizarana loharano mitovy; tazonina raha shared/Commons, raha tsy izany ajanona mandra-pahamarina.\n"
    (J/'notes.wiki').write_text(notes,encoding='utf-8')
    print('sections',len(plan),'links',len(mapping),'verified',sum(bool(x) for x in mapping.values()),'images',len(images))
    print('nonshared',[(k,v) for k,v in images.items() if v['repository']!='shared'])


if __name__=='__main__':
    main()
