"""Offline section plan; source anomalies must be resolved before publication."""
from pathlib import Path
import shutil
import mwparserfromhell as mw
from mgwiki_editor.core import write_json

JOB = Path('runs/mahabharata-20261108')
PLAN = [('00-lead',1,33),('01-textual-intro',34,44),
        ('02-redaction',45,56),('03-historical-references',57,66),
        ('04-books',67,172),('05-history',173,187),
        ('06-synopsis-intro',188,195),('07-ancestors',196,204),
        ('08-princes',205,215),('09-lac-house',216,220),
        ('10-marriage',221,225),('11-indraprastha',226,232),
        ('12-dice',233,238),('13-exile',239,243),('14-battle',244,254),
        ('15-end',255,263),('16-reunion',264,266),('17-themes',267,272),
        ('18-translations',273,309),('19-critical-edition',310,312),
        ('20-literature',313,317),('21-screen',318,328),
        ('22-radio',329,331),('23-folk',332,334),('24-jain',335,340),
        ('25-family',341,343),('26-influence',344,348),
        ('27-modern-translations',349,374),('28-notes',375,377),
        ('29-citations',378,380),('30-sources',381,413),('31-external',414,441)]

if __name__ == '__main__':
    text=(JOB/'source.wiki').read_text()
    lines=text.splitlines(keepends=True)
    records=[]
    for ident,start,end in PLAN:
        directory=JOB/'sections'/ident
        directory.mkdir(parents=True,exist_ok=True)
        (directory/'source.wiki').write_text(''.join(lines[start-1:end]))
        records.append(dict(id=ident,start=start,end=end,directory=str(directory),
                            status='pending',local_content='none'))
    write_json(JOB/'section-plan.json', records)
    shutil.copyfile('data/country-names.json',JOB/'country-names.json')
    code=mw.parse(text)
    write_json(JOB/'source-link-inventory.json',[
        dict(target=str(l.title),label=str(l.text or l.title)) for l in code.filter_wikilinks()])
    files=[str(l.title).split(':',1)[1].strip() for l in code.filter_wikilinks()
           if str(l.title).lower().startswith(('file:','image:'))]
    files.insert(0,'Kurukshetra.jpg')
    write_json(JOB/'source-image-inventory.json',files)
    (JOB/'shared-references.wiki').write_text('\n\n'.join(str(t) for t in code.filter_tags()
        if str(t.tag)=='ref' and t.has('name') and not t.self_closing))
    notes='''= Fanamarihana momba ny fanitsiana =
== Fanasokajiana sy fiaviana ==
Lahatsoratra vaovao: tsy misy ny Mahabharata malagasy na ny sandbox. Tsy misy rohy mg ao amin' ny interlanguage anglisy voamarina tamin' ny API voafetra ho mg. Mahabharata no lohateny nangatahin' ny mpampiasa. existing_preserved: tsy misy votoaty eo an-toerana hotambatra.
Loharano: https://en.wikipedia.org/w/index.php?oldid=1384087555 ; Wikipedia anglisy sy ireo mpandray anjara, CC BY-SA 4.0. Tsy nosokafana ny rohy ivelany, sary na loharano bibliografika. Ny metadata voatahiry ihany no nodinihina; tsy filazana fa novakina ny boky voatanisa izany.
Ny init voalohany dia tapaka noho ny fakana siteinfo tsy ilaina tamin' ny langlinks rehetra; tsy nisy job na snapshot voasoratra. Ny helper manaraka dia nampiasa ny Wiki gateway sy lllang=mg, tsy nanova ny mpiambina na pacing.
== Olana tokony hodinihina ==
* source.wiki 63–65: ref :0 dia mitondra lohateny sy URL momba ny quotas ho an' ny Marathas, nefa ampiasaina amin' ny tantaran' ny literatiora sanskrita sy soratra varahina. Tsy heverina ho voamarina ny fanohanana: mila porofo Wikipedia fanampiny; tsy azo mamorona solony na manokatra ilay URL.
* source.wiki 347: milaza fa nahazo Jnanpith tamin' ny 1972 ny Rashmirathi; mila fanamarinana amin' ny Wikipedia azo idirana satria mety mifangaro amin' ny sanganasa hafa.
* source.wiki 291–292: misy litera simba ao amin' ny anaran' ny mpanoratra bibliografika. Tsy ahitsy amin' ny vinavina.
* source.wiki 342: mila tehirizina sy vakina ny Kuru family tree alohan' ny fandikana ilay tabilao nampidirin' ny template.
== Drafitra fizarana ==
'''
    for r in records:
        notes+=f"* {r['id']}: source.wiki {r['start']}–{r['end']}; {r['directory']}; miandry; tsy misy existing/sandbox. Ny fizarana 02–04 manohy 01; 07–16 manohy 06; 18–24 manohy ny lohateny lehibe 18. Ref iombonana ao shared-references.wiki.\n"
    notes+='''== Fandaminana iombonana ==
Ny ref dia tehirizin' ny worker amin' ny toerana misy azy; ny coordinator irery no mampifanaraka ny template bibliografika amin' ny wikitext tsotra. Ny rohy anglisy dia marihina sy tehirizina mandra-pahazoana target malagasy voamarina; tsy afaka avoaka ho rohy mg tsy voamarina. Tsy afindra ny maintenance, navigation, authority-control sy sokajy anglisy tsy voamarina. Ny sary sy rohy rehetra dia ao amin' ny inventory, mila fanisana rehefa atambatra.
Ny Mahabharata dia lohatenin-tsanganasa, atao sora-mandry; ny mpanoratra araka ny lovantsofina ihany no iantsoana an' i Vyasa. Tsy avadika ho zava-nitranga voaporofo ara-tantara ny tantara ao anatiny. India no fanoratra ao amin' ny cache firenena voatahiry. Ny daty BCE/CE adika ho tal. J.K./taor. J.K. ary hazavaina amin' ny fanononana voalohany.
'''
    (JOB/'notes.wiki').write_text(notes)
    (JOB/'shared-context.wiki').write_text(notes)
