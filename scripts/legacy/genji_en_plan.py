"""Offline section plan; never performs remote operations."""
import json
from pathlib import Path

import mwparserfromhell as mw

from mgwiki_editor.core import write_json

JOB = Path("runs/genji-en-20261105-utf8")
PLAN = [
    ("00-lead", 1, 45, "Fampidirana sy mombamomba ny boky"),
    ("01-history", 46, 53, "Toe-javatra ara-tantara"),
    ("02-authorship", 54, 63, "Mpanoratra"),
    ("03-plot", 64, 85, "Ny tantara"),
    ("04-completion", 86, 93, "Fahafenoan' ny tantara"),
    ("05-literary", 94, 102, "Toe-javatra ara-literatiora"),
    ("06-outline", 103, 114, "Firafitra sy drafitra ankapobeny"),
    ("07-chapters", 115, 493, "Lisitry ny toko"),
    ("08-manuscripts", 494, 513, "Sora-tanana"),
    ("09-scrolls", 514, 521, "Horonana misy sary"),
    ("10-japanese", 522, 532, "Mpamaky amin' ny vanim-potoana ankehitriny: teny japoney"),
    ("11-other-translations", 533, 549, "Dikan-teny tsy anglisy"),
    ("12-english", 550, 561, "Dikan-teny anglisy voafantina"),
    ("13-reception", 562, 574, "Fandraisana sy lova"),
    ("14-adaptations", 575, 594, "Fampifanarahana amin' ny endrika hafa"),
    ("15-related", 595, 608, "Jereo koa"),
    ("16-references", 609, 614, "Fanamarihana sy loharano"),
    ("17-bibliography", 615, 1016, "Boky sy lahatsoratra"),
    ("18-external", 1017, 1046, "Rohy ivelany sy sokajy"),
]


def run():
    source = (JOB / "source.wiki").read_text(encoding="utf-8")
    lines = source.split("\n")
    records = []
    for section_id, start, end, title in PLAN:
        directory = JOB / "sections" / section_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "source.wiki").write_text("\n".join(lines[start-1:end])+"\n", encoding="utf-8")
        records.append({"id": section_id, "start": start, "end": end, "heading": title,
                        "directory": str(directory), "status": "pending", "local_context": "none"})
    write_json(JOB / "section-plan.json", records)
    refs = [str(tag) for tag in mw.parse(source).filter_tags()
            if str(tag.tag).lower() == "ref" and tag.has("name") and not tag.self_closing]
    (JOB / "shared-references.wiki").write_text("\n\n".join(refs)+"\n", encoding="utf-8")
    (JOB / "shared-context.wiki").write_text("""= Toromarika iombonana =
Lohateny nangatahin' ny mpampiasa: Tantaran'i Genji. Ao amin' ny fehezanteny vaovao: ''Tantaran' i Genji'' araka ny elanelana amin' ny apostrôfa. Tsy anarana ofisialin' ny dikan-teny efa nivoaka io lohateny malagasy io.
Loharano: Wikipedia anglisy The Tale of Genji, revision 1381255844. Tsy misy lahatsoratra na sandbox amin' ny lohateny vaovao. Nofafana araka ny fangatahana ny lahatahiry sy script Genji japoney teo aloha; tsy nentina tao amin' ity dika vaovao ity.
Mpandrindra irery no manambatra sy mikaroka. Tsy mahazo mikaroka lavitra ny mpiasa, mamafa asa hafa, manova rakitra iombonana, manendry mpiasa hafa, manomana na mamoaka. Ireo rakitra section.wiki, notes.wiki, vocabulary.json ao amin' ny lahatahiry voatokana ihany no soratana.
Tazomy mandritra ny fanoratana ny rohy anatiny anglisy izay efa ao amin' ny loharano. Ny mpandrindra no hamadika azy ho rohy malagasy voamarina, na ho soratra tsotra miaraka amin' ny fanazavana ao amin' ny notes. Aza mamorona rohy vaovao tombantombana. Tazomy ny anaran-drakitra sary, toerana, ref ary metadata. Tsy misy sary alaina.
Tazomy tsy misy fanovana aloha ny môdely citation ao amin' ny ref sy bibliography; hovadihin' ny mpandrindra ho native wikitext tsy miteraka sokajy. Esory ny maintenance templates, portal, authority control, navboxes. Tsy mahazo Sokajy miasa na DEFAULTSORT.
Anarana japoney: Murasaki Shikibu, Yosano Akiko (samy hita ao amin' ny source), Fujiwara no Michinaga, Fujiwara Teika, Minamoto no Chikayuki. Aza mamadika anarana kisendrasendra; soraty ao amin' ny notes ny endrika japoney mbola mila porofo. Tazomy ny bibliographic metadata, na inona na inona filaharany.
Firenena: Japàna, Frantsa, Alemaina, Italia, sns araka ny country-names.json. Aza manova anaran-tany ao amin' ny citation/titre.
Teny atolotra amin' ny famaritana: courtier = tandapa; concubine = vadikely; manuscript = sora-tanana; scroll = horonana; vernacular = fiteny andavanandro tamin' izany fotoana izany; homophone = teny mitovy fanonona nefa samy hafa hevitra; allusion = firesahana ankolaka; regent = mpitondra misolo ny emperora; feudal = mifototra amin' ny fatorana eo amin' ny tompom-pahefana sy ny olona miankina aminy. Tsy voatery teny rakibolana voamarina ireo: hamarinina amin' ny porofo lookup.
Ref name Tyler dia faritana ao amin' ny section 12-english; mety ampiasaina mialoha ao amin' ny authorship. Aza mamorona ref vaovao. Vakio shared-references.wiki raha ilaina. Ny citation rehetra dia eo amin' ny filazana tohanany.
Fanitsiana mazava tokony hotandremana: Waley tsy dika feno (tsy ao ny toko 38). Ao amin' ny Authorship, ny diary entry 1008 dia manaporofo fa efa nisy ampahany amin' ny TALE, fa tsy hoe 'diary' efa nisy tamin' ny diary; mariho io fanitsiana diso fanondro ao amin' ny source io. Aza mampiditra filazana vaovao tsy voaporofo. Ny fomba fiteny manome lanja sy consensus tsy misy loharano dia avoahy ho hevitry ny mpitsikera fa tsy feon' ny rakipahalalana.
Ny teny nalaina adika amin' ny teny malagasy dia asiana fanamarihana hoe dikan-teny. Tsy ovaina ny original title sy citation metadata.
""", encoding="utf-8")
    state = json.loads((JOB / "job.json").read_text(encoding="utf-8"))
    notes = ["= Fanamarihana momba ny fanitsiana =", "",
             "== Fidirana sy fampitahana ==",
             "Asa vaovao avy amin' ny Wikipedia anglisy; lohateny nangatahana: Tantaran'i Genji.",
             f"Loharano raikitra: {state['source']['url']}. Creative Commons Attribution-ShareAlike; ny rohy permanent dia hiditra amin' ny edit summary.",
             "Tsy misy lahatsoratra malagasy na sandbox amin' ny lohateny nangatahana; samy novakiana tanteraka ireo snapshots banga.",
             "Nofafana araka ny fangatahan' ny mpampiasa ny runs/genji-ja-20261104 sy runs/genji-ja-20261104-sections ary ireo script valo mifandray aminy. Tsy nisy pejy lavitra nofafana.",
             "Tsy nisy rohy citation na ivelany nosokafana. Ny metadata ihany no tehirizina; tsy milaza ho namaky ireo loharano ivelany.",
             "Ny lohateny dia tazonina amin' ny fanoratra nangatahana; elanelana amin' ny apostrôfa ampiharina amin' ny prose vaovao.",
             "", "== Drafitra voalahatra =="]
    for r in records:
        notes.append(f"* {r['id']}: andalana {r['start']}–{r['end']}, {r['heading']}; {r['directory']}; tsy misy votoaty eo an-toerana; miandry. Miankina amin' ny shared-references sy fanamarinana rohy farany.")
    (JOB / "notes.wiki").write_text("\n".join(notes)+"\n", encoding="utf-8")
    print(len(records), "section assignments planned")


if __name__ == "__main__":
    run()
