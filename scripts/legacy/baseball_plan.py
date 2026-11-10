"""Offline Baseball section assignments and loss-accounted reference scaffolding."""
import json
import re
import textwrap
from pathlib import Path

import mwparserfromhell as mw

from mgwiki_editor.core import write_json

JOB = Path('runs/baseball-20261106')
PLAN = [
    ('00-lead', 1, 39), ('01-overview', 40, 58),
    ('02-fielding', 59, 62), ('03-offense', 63, 71),
    ('04-defense', 72, 77), ('05-order', 78, 85),
    ('06-personnel', 86, 108), ('07-strategy', 109, 113),
    ('08-tactics', 114, 127), ('09-origins', 128, 137),
    ('10-us-history', 138, 158), ('11-world-history', 159, 175),
    ('12-distinctive', 176, 204), ('13-statistics', 205, 252),
    ('14-culture-us', 253, 266), ('15-latin-caribbean', 267, 276),
    ('16-asia', 277, 286), ('17-europe-oceania', 287, 294),
    ('18-africa', 295, 299), ('19-children', 300, 304),
    ('20-popular-culture', 305, 317), ('21-derivatives', 318, 333),
    ('22-see-also', 334, 354), ('23-citations', 355, 360),
    ('24-bibliography', 361, 397), ('25-further', 398, 405),
    ('26-external', 406, 458),
]


def main():
    source = (JOB / 'source.wiki').read_text(encoding='utf-8')
    lines = source.split('\n')
    refs = {}
    plan = []
    for sid, start, end in PLAN:
        d = JOB / 'sections' / sid
        d.mkdir(parents=True, exist_ok=True)
        raw = '\n'.join(lines[start-1:end])+'\n'
        (d / 'source.wiki').write_text(raw, encoding='utf-8')
        code = mw.parse(raw)
        for tag in list(code.filter_tags()):
            if str(tag.tag).lower() != 'ref':
                continue
            name = str(tag.get('name').value).strip('"\' ') if tag.has('name') else f'baseball-{len(refs)+1:03d}'
            group = str(tag.get('group').value).strip('"\' ') if tag.has('group') else ''
            if not tag.self_closing:
                key = group+'|'+name
                body = str(tag.contents)
                if key in refs and refs[key]['body'] != body:
                    raise RuntimeError('Conflicting named reference: '+key)
                refs[key] = {'name': name, 'group': group, 'body': body, 'section': sid}
            replacement = f'<ref name="{name}"'+(f' group="{group}"' if group else '')+' />'
            code.replace(tag, replacement)
        text = str(code)
        # Explicit user authorization: omit only disputed passages, retain other content.
        if sid == '18-africa':
            text = re.sub(r'There is also a Africa Baseball Academy.*?<ref[^>]+/>\s*', '', text)
            text = re.sub(r'The Dodgers operate.*?<ref[^>]+/>\s*', '', text)
        if sid == '15-latin-caribbean':
            text = re.sub(r'In 2017, 83 .*?<ref[^>]+/>\s*', '', text)
        if sid == '16-asia':
            text = re.sub(r'Revenue figures are not released.*?<ref[^>]+/>\s*', '', text)
        if sid == '12-distinctive':
            text = text.replace(' - nearly an hour shorter than before the introduction of a pitch clock.', '.')
        (d / 'translation-source.wiki').write_text(text, encoding='utf-8')
        (d / 'readable-source.txt').write_text('\n'.join('\n'.join(textwrap.wrap(l,150,replace_whitespace=False,drop_whitespace=False,break_long_words=False,break_on_hyphens=False)) for l in text.splitlines())+'\n', encoding='utf-8')
        plan.append({'id':sid,'start':start,'end':end,'directory':str(d),'status':'pending'})
    write_json(JOB / 'reference-definitions.json', refs)
    write_json(JOB / 'section-plan.json', plan)
    (JOB / 'shared-context.wiki').write_text("""= Toromarika iombonana =
Loharano: Baseball anglisy, fanitsiana 1383601251. Lahatsoratra malagasy vaovao Baseball; samy tsy misy ny mainspace sy sandbox. Ny mpandrindra efa namaky ny loharano manontolo sy ireo snapshot foana.
Mpiasa ivelan-tambajotra ihany: tsy misy fetch, lookup, subagent, prepare, publish, na fanoratana rakitra iombonana. Ny section.wiki, notes.wiki, vocabulary.json ao amin’ ny directory voatokana ihany no soratana. Ny mpandrindra no manambatra, manamarina ary mamoaka.
Vakio translation-source.wiki feno (readable-source.txt mitovy votoaty, fohy andalana, raha lava ny andalana). Ny source.wiki no original; ny translation-source dia manolo ny ref rehetra ho selfclosing fotsiny. Ny mpandrindra no hamerina ny famaritana rehetra avy amin’ ny reference-definitions.json ao amin’ ny fizarana citations. AZA very na ovaina ny ref names na citation positions. Tazomy ny citation templates ao bibliography; ho native wikitext ny fampifanarahana farany.
Rohy anatiny: tazomy ny kendrena anglisy, adika ny label; mpandrindra hanolo ho mg voamarina, na soratra tsotra voarakitra raha tsy misy target. Sary: filenames tsy ovaina, caption/alt adika; ireo sary rehetra ao source tazonina. Aza mamorona template malagasy tsy voamarina; native wikitext tsara kokoa. Esory maintenance, navboxes, authority, portal, live categories; mpandrindra hampiditra sokajy voamarina inert amin’ ny farany. Tsy mila mandika ireo navbox transcluded tsy ao anatin’ ny source.
Teny iombonana descriptive (tsy rakibolana manamarina): baseball = baseball (teny vahiny, atao italics ao prose rehefa tsy bold subject); bat = kibay fikapohana; ball = baolina; base = toby; home plate = takelaka fiaingana; pitcher = mpanipy; catcher = mpisambotra ao ambadiky ny mpikapoka; batter = mpikapoka; runner = mpihazakazaka; fielder = mpiaro; run = isa iray azo rehefa vita ny fihodinana ny toby efatra; out = fanesorana mpilalao amin’ ny fanafihana amin’ io anjara io; inning = fihodinana lalao ahitana ny anjaran’ ny ekipa roa mifandimby manafika sy miaro; half-inning = antsasaky ny fihodinana; strike = ''strike'' (manazava araka ny fitsipika); ball amin’ ny fanisana pitches = ''ball'' (fanipazana tsy ao amin’ ny faritra voafaritra sady tsy niezahana nokapohina); home run = ''home run'' (kapoka ahafahana mamita ny fihodinana ny toby efatra). Efa hojerena amin’ ny lookup avy amin’ ny mpandrindra ireo; mpiasa mirakitra famaritana EN tsotra, dika MG, status descriptive ary mila lookup amin’ ny vocabulary.json. Aza milaza fa teny ara-teknika malagasy efa raikitra ny teny famaritana.
MLB = Major League Baseball (Ligy Lehibe amin’ ny Baseball); NL = National League (Ligim-pirenena); AL = American League (Ligy Amerikanina); WBSC = World Baseball Softball Confederation (Konfederasiona Iraisam-pirenena momba ny Baseball sy Softball). Tazomy acronym ary omeo gloss voalohany amin’ ny fizarana raha ilaina. Full foreign institution name italic + Malagasy gloss. Aza ovaina ny filaharan’ ny anaran’ olona; Sadaharu Oh endrika evidenced source, aza mamadika anarana tsy misy porofo. Firenena: vakio country-names.json; ny tsy hita/ambiguous dia tazomy source link label ho an’ ny coordinator fa aza mamorona anarana.
Elision spacing: amin' ny, an' ny, ho an' ny. Italics teny vahiny sy boky/sarimihetsika/paper titles; citation metadata originals tsy ovaina. Teny nalaina adika asiana dikan-teny, aza manitatra na manova hevitry ny olona.
Ny mpampiasa nanaiky hanala ireo ampahany mampiahiahy. Efa nesorina ao translation-source ireo filazana momba ny akademia Nairobi/Nigeria sy Dodgers/Mpigi, stats 2017 citation2015, ary ny filazana rafitra amateur tsy mazava firenena ao Asia. Tsy esorina ny sisa amin’ ireo fizarana. Nesorina koa ilay fampitahana ora iray tsy mifanaraka amin’ ny salanisa (mitazona ny tarehimarika samihafa). Aza averina ireo. Notes dia milaza omissions araka ny fangatahana, tsy porofo fa diso ireo reference titles.
Lahatsoratra feno amin’ ny teny malagasy, tsy famintinana na lisitra telegraphique. Ataovy feno ny paragraphs, dates, numbers, qualifications, captions, links ary ref rehetra. Notes/vocab tsy ao amin’ ny lahatsoratra. Mbola tsy final editorial approval ny completion.
""", encoding='utf-8')
    with (JOB / 'notes.wiki').open('a', encoding='utf-8') as f:
        f.write('\n== Fanohizana araka ny fangatahana ==\nNy mpampiasa nangataka ny hanesorana ilay ampahany mampiahiahy. Esorina ireo filazana voalaza manokana etsy ambony; tazonina ny sisa. Tsy sakana intsony ny filazana nesorina, nefa mbola takina ny vavahady rehetra amin’ ny dika farany.\n')
        for x in plan:
            f.write(f"* {x['id']}: {x['start']}–{x['end']}; {x['directory']}; miandry; fiankinana: reference-definitions.json, shared-context.wiki, fampifanarahana rohy sy teny farany.\n")
    write_json(JOB / 'status.json', {'status':'translating','user_authorized_omissions':True})


if __name__ == '__main__':
    main()
