"""Explicit coordinator corrections after reading all section handoffs."""
from pathlib import Path
import re

import mwparserfromhell as mw

from mgwiki_editor.core import write_json, lint_wikitext

J=Path('runs/achilles-20261107')


def main():
    text=(J/'draft.wiki').read_text(encoding='utf-8')
    # Protect complete references, URLs, filenames, work titles and original-script quotations.
    saved=[]
    pattern=r'<ref\b[^>]*/\s*>|<ref\b[^>]*>.*?</ref>|<nowiki\b[^>]*>.*?</nowiki>|\[\[(?:File|Image):[^|\]]+|https?://[^\s\]<>|]+|\'\'[^\n]*?\'\''
    def protect(m):
        saved.append(m[0]);return f'\x00P{len(saved)-1}\x00'
    prose=re.sub(pattern,protect,text,flags=re.S|re.I)
    prose=prose.replace('[[Trôia|Troy]]','[[Trôia]]')
    prose=re.sub(r'\bTroy\b','Trôia',prose)
    prose=prose.replace('Austria','Aotrisy')
    prose=prose.replace('ny Akeana','ny Grika').replace('ny Akaiana','ny Grika').replace('ny Achaeans','ny Grika').replace('tafika akeana','tafika grika')
    prose=prose.replace('môzaika romana','môzaika rômana').replace('sary romanina','sary rômana').replace('emperora romana','emperora rômana')
    prose=prose.replace('maty tsy tonga taona',"maty talohan' ny fotoana")
    for i,value in enumerate(saved):prose=prose.replace(f'\x00P{i}\x00',value)
    text=prose
    # These foreign labels are new translated prose, not original-source quotations/titles.
    text=text.replace("iray amin' ny Nereid", "iray amin' ireo ''Nereid''")
    text=text.replace('ireo Nereids (andriamanibavin-dranomasina)',"ireo ''Nereid'' (andriamanibavin-dranomasina)")
    text=text.replace("ny ''Achaean'', [...]",'ny Grika, [...]')
    text=text.replace("mpitari-tafika ''Achaean'', izany hoe ireo Grika ao amin' ny tononkalo", "mpitari-tafiky ny Grika, izay antsoin' i Homer hoe ''Achaeans'' ao amin' ny tononkalo")
    text=text.replace("=== Ao amin' ny traikeodia grika ===", "== Ny fandraisana azy tamin' ny Andro Taloha ==\n\n=== Ao amin' ny traikeodia grika ===",1)
    # Restore the one omitted source reference, using the pinned LSJ expansion.
    old="(in Greek)</ref>\nToy ny an' ireo olona sasany"
    new="(in Greek)</ref><ref>[https://www.perseus.tufts.edu/hopper/text?doc=Perseus:text:1999.04.0057:entry=xai/th χαίτη]. Liddell, Henry George; Scott, Robert; ''A Greek–English Lexicon'', Perseus Project.</ref>\nToy ny an' ireo olona sasany"
    assert old in text
    text=text.replace(old,new,1)
    # The source's uncited setting of the morning star is not asserted as Homeric fact.
    old="Mirehitra mandra-pilentik' i Phosphorus, ilay kintana amin' ny maraina hita any atsinanana, izay Venosy koa, ny antontan-kitay fandoroana ny faty; lazain' ny tononkalo fa midina io kintana io."
    new="Voatonona amin' ny filazalazana ny fandoroana ny faty koa i Phosphorus, ilay kintana amin' ny maraina hita any atsinanana, izay Venosy ihany koa."
    assert old in text
    text=text.replace(old,new)
    text=text.replace("''Rider of Red'' i Achille", "''Rider of Red'' (mpitaingina mena) i Achille")
    text=text.replace("tantara foronina japoney natao ho mora vakina", "karazana tantara foronina japoney")
    text=text.replace("sambo mpiady karazana ''cruiser'' mifono vy", "sambo mpiady mifono vy karazana ''cruiser'', izany hoe sambo mpiady antonony habe afaka mandeha lavitra")
    text=text.replace("HMNZS (sambo an' ny mpanjaka avy any Zelandy Vaovao) ''Achilles''", "HMNZS (sambo an' ny mpanjaka avy any Zelandy Vaovao) ''Achilles'' (70)")
    text=text.replace("HMS ''Ajax'' sy HMS ''Exeter''", "HMS ''Ajax'' (22) sy HMS ''Exeter'' (68)")
    text=text.replace("mozean' i Louvre",'Tranombakoka Louvre')
    text=text.replace("''ambrosia'' tamin' ilay zazalahy", "''ambrosia'' (sakafo lazain' ny angano fa fihinan' ny andriamanitra) tamin' ilay zazalahy")
    text=text.replace("''pastel'' teo amin' ny taratasy", "loko maina atao hoe ''pastel'' teo amin' ny taratasy")
    text=text.rstrip()+"\n[[:Sokajy:Angano grika]]\n"
    (J/'draft.wiki').write_text(text,encoding='utf-8')
    with (J/'notes.wiki').open('a',encoding='utf-8') as f:
        f.write("""\n== Fampiraisana sy fanamarinana nataon' ny mpandrindra ==
Vita sy voaray ireo fizarana 25; nosoratana indray ireo tsy feno ihany, tamin' ny alalan' ny fanendrena fanitsiana voafaritra. Ny corrected-section-plan.json no mamaritra ny sehatra marina. Tsy misy fizarana nesorina na naverina novokarina ho lahatsoratra iray manontolo. Ny section-handoff-notes.wiki sy section-vocabulary.json no mitahiry ny fanolorana sy ny fetrany tany am-boalohany; ny fanapahan-kevitra eto sy ny vocabulary.json farany no mandrindra azy ireo.
Nohamarinin' ny mpandrindra ny sombin-dahatsoratra rehetra sy ny snapshots feno. Nampidirina ny lohateny ambony momba ny fandraisana tamin' ny Andro Taloha; tsy naverina ireo lohateny avy amin' ny fanapahana andalana diso. Feno ny mozika sy ny Deidamia; ny fizarana sarimihetsika ihany no mitazona ireo mpilalao valo. Naverina ny ref LSJ χαίτη iray tsy tafiditra tamin' ny fanolorana 02. Mitovy amin' ny loharano ny isan' ny ref 143 aorian' izany.
Notazonina ny teny nindramina sy lohateny vahiny amin' ny sora-mandry; tsy novaina ny anarana/filaharana ao amin' ny metadata na ny teny nalaina. Nampiraisina ho Trôia ny anaran-tanàna amin' ny lahatsoratra vaovao, fa tsy ny lohateny/URL/fanononana. Ny Achaeans ao amin' ny sanganasan' i Homer dia hazavaina ho ireo Grika; tsy noforonina ho foko maoderina. Ny Nereid sy ny môzaika dia nampifanarahana. Voahitsy ho maty talohan' ny fotoana ny untimely death fa tsy fahafatesan-jaza tsy ampy taona.
Ny source dia milaza fa milentika i Phosphorus, kintana amin' ny maraina, mandritra ny fandoroana an' i Patroclus, nefa tsy misy fanondroana manokana manohana izany fitodihana izany. Tsy nampidirina ho filazan' i Homer voamarina io antsipiriany mampiahiahy io; voatazona ny fampitahana Hesperus sy ny fanononana Phosphorus ary ny maha-Venosy azy roa. Tsy noforonina ny fanitsiana vaovao momba ny fotoana tena nitrangan' izany.
Ny Chryseis ao amin' ny filazana ny tantaram-pitiavana tamin' ny Moyen Âge dia tsy nampitovina tamin' i Criseyde/Cressida; nesorina io fanondroana anarana io ihany ary notazonina ny lohateny sy ny filazana ny fiaviana tamin' ny Andro Antenatenany. Porofo Wikipedia voatahiry: evidence/troilus-name-clarification.json sy troilus-clarification.wiki; tsy nosokafana ny boky na URL ivelany. Ny omphalos dia nohazavaina ho vato masina eo amin' ny alitara, fa tsy nolazaina fa foiben' izao tontolo izao i Thymbra.
Ny filename misy München dia ilay rakitra Commons iray ihany, voasoratra amin' ny anarana tena voamarina fa tsy encoding %C3%BC tsy nisy. Commons metadata: evidence/decoded-file.json; CC BY-SA 4.0, imagerepository=shared. Tsy nomena licence vaovao na nampidirina sary tsy malalaka. Ny sary 37 hafa dia Commons shared miaraka amin' ny licence malalaka ao evidence/files-000.json. Ny filazana fameperana fitsidihana mozea ao amin' ny description dia tsy novana ho filazana licence tsy malalaka mifanohitra amin' ny Commons licence.
Ny caption diso Berlin ho an' ny Staatliche Antikensammlungen ao amin' ny gallery dia natao Munich araka ny metadata Commons; ny akanjon' i Thetis amin' ny vola madinika dia nohazavaina araka io metadata io fa tsy noheverina fa mitafy ampinga izy. Tsy nisy sary nosokafana na nalaina tamin' ny tambajotra. Ny sary 38 dia voatahiry avokoa, miaraka amin' ny caption voadika.
Voatahiry amin' ny endriny ny sokajy efa misy, afa-tsy ny colon fiarovana. Nampiana any amin' ny farany [[:Sokajy:Angano grika]], voamarina ao evidence/local-topic-pages.json. Tsy naverina ny sokajy anglisy, navigation, maintenance, authority-control na sister-project logos izay singa fampisehoana fa tsy sary mitantara. Ny rohy sister-project sy ireo loharano dia navadika ho rohy ivelany tsy miteraka sokajy.
Firenena: ampiasaina ny cache voatahiry country-names.json; tsy ao amin' ny cache i Aotrisy ka nohamarinina tamin' ny pejy mg Aotrisy, revision1120590, ao evidence/local-topic-pages.json. Tsy porofon' ny fiandrianam-pirenena ny maha-mpikambana amin' ny sokajy. Tsy novaina ny firenena/anaran-toerana ao amin' ny metadata, quotation, URL na lohateny.
Tsy nosokafana na nohamarinina an-tserasera ny citation URLs, DOI, sary, archive na Freebase. Ny fanamarinana dia momba ny fifandraisan' ny filazana sy ny fanononana voatahiry, ny metadata, ny fifanarahan' ny ref, ary ny fidelity amin' ny loharano Wikipedia; tsy filazana fa novakina ny boky tany am-boalohany.
""")
    code=mw.parse(text)
    refs=[t for t in code.filter_tags() if str(t.tag)=='ref']
    write_json(J/'reconciled-structural-audit.json',dict(lint=lint_wikitext(text),refs=len(refs),templates=[str(t.name) for t in code.filter_templates()],bytes=len(text.encode())))
    print((J/'reconciled-structural-audit.json').read_text(encoding='utf-8'))


if __name__=='__main__':main()
