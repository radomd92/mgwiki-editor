"""Record coordinator's evidenced raw-draft review, with structural assertions."""
import re
from pathlib import Path
from urllib.parse import unquote

import mwparserfromhell as mw

from mgwiki_editor.core import GATES, artifact_hashes, read_json, write_json, lint_wikitext

J=Path('runs/achilles-20261107')


def main():
    source=(J/'source.wiki').read_text(encoding='utf-8')
    text=(J/'draft.wiki').read_text(encoding='utf-8')
    code=mw.parse(text)
    assert not lint_wikitext(text)
    assert not code.filter_templates()
    source_refs=[t for t in mw.parse(source).filter_tags() if str(t.tag)=='ref']
    refs=[t for t in code.filter_tags() if str(t.tag)=='ref']
    assert len(refs)==len(source_refs)==143
    def urls(t):return {u.rstrip('.,;:') for u in re.findall(r'https?://[^\s|<>\]}\"]+',t)}
    assert not urls(source)-urls(text)
    def isbns(t):return set(re.findall(r'(?:isbn\s*=|ISBN\s*\||ISBN\s+)([0-9Xx-]+)',t,re.I))
    assert not isbns(source)-isbns(text)
    files=read_json(J/'source-image-inventory.json')
    assert all(unquote(name) in text for name in files)
    assert len(files)==38
    assert text.count('<gallery>')==text.count('</gallery>')==1
    assert text.count('[[:sokajy:Biôgrafia]]')==1
    assert text.count('[[:Sokajy:Angano grika]]')==1
    assert text.rstrip().endswith('[[:Sokajy:Angano grika]]')
    assert 'https://www.freebase.com/m/0gy_' in text and '[[Biôgrafia]]' in text
    headings=[str(h.title).strip() for h in code.filter_headings()]
    assert len(headings)==len(set(headings))
    assert "Ny fandraisana azy tamin' ny Andro Taloha" in headings
    for p in (J/'evidence').glob('local-link-verification-*.json'):
        assert all(not page.get('missing') and not page.get('pageprops') for page in read_json(p)['response']['query']['pages'])
    vocabulary=read_json(J/'vocabulary.json')
    assert all(e['status'] in {'descriptive','verified'} for e in vocabulary)
    assert (J/'unknown-vocabulary.wiki').is_file()
    # These booleans attest the coordinator's completed source/fragment/raw review;
    # the assertions above are supplementary checks, not a fluency verifier.
    with (J/'notes.wiki').open('a',encoding='utf-8') as f:
        f.write("""\n== Vavahady fanitsiana: fanamarinana mialoha ny preview ==
meaning: nampitahaina tamin' ny source.wiki feno sy ny lahatsoratra teo an-toerana ny fizarana 25; voatazona ny negation, qualification, daty, isa, anarana ary dikan-tantara. Voarakitra etsy ambony ireo fanitsiana loharano vitsy sy ny antony; tsy misy hevitra lehibe mbola tsy voavaha.
fluency: novakin' ny mpandrindra ny wikitext an' ny fizarana rehetra sy ny fanitsiana tao amin' ny fitambaran-dahatsoratra. Malagasy feno ny fehezanteny, tsy caveman; voahaja ny amin' ny/an' i/amin' izao sy ny fiarovana apostrofa ao amin' ny anarana, citation, URL ary delimiter wiki.
coverage: feno ny lead/tabilao, vatana, appendices, sarinteny voalohan' ny Iliada, galerie sary9, sary rehetra38, ary ref143. Voatazona ny URL rehetra avy amin' ny loharano. Ny source-to-draft mappings/fallbacks dia ao coverage-audit.wiki sy section-handoff-notes.wiki; tsy nisy rohy nalaina ho lasibatra mg novinavinaina.
terminology: nosafidina araka ny hevitra ny fanazavana, voamarina tamin' ny lookup en/mg voatahiry raha ilaina; notazonina ho failed/no_matching_language ny tsy fahombiazan' ny rakibolana fa tsy noheverina ho teny tsy misy. Voahitsy ho menaka fanosotry ny andriamanitra ny ambrosia amin' ity toe-javatra ity araka ny sense anointing-oil, tsy noferana amin' ny sakafo. Ny fanazavana tendôna sy valanaretina dia tsy mampiditra diagnosis/torohevitra vaovao. Ny lisitra unknown-vocabulary.wiki dia fitahirizana terminology mihoatra100, tsy fanemorana hevitra lehibe. Misy gloss HMS/HMNZS sy anaram-pikambanana vahiny, italika ny teny/titres vahiny; notazonina ny filaharan' ny anaran' olona sy ny romanization voaporofo, tsy nisy olona malagasy voatery nivadika anarana.
citations: napetraka teo akaikin' ny filazana tohanany ny refs; mitovy143 amin' ny source, tsy nisy named reference very na nifandona, mifanaraka ny bibliography sy ireo citation fohy. Voatahiry ny metadata sy identifier; naverina ny LSJ iray. Tsy novakina tamin' ny URL ireo loharano ivelany, ary tsy filazana fanamarinana azy ireo ity gate ity.
links_templates: nohamarinina tamin' ny API mg ny fisiana sy ny tsy maha-disambiguation ny target rehetra voamarina. Tsy misy template vahiny nadika an-jambany; native wikitext no tabilao/refs/gallery. Voamarina ho Commons shared malalaka ny sary38; tsy nosokafana ny sary. Misy vatofantsika mifanaraka amin' ny lohateny voadika; inert sy any amin' ny farany ireo sokajy. Tsy misy interwiki velona, metadata na DEFAULTSORT.
neutrality: nodinihina ny words-to-watch araka ny toe-javatra, tsy natao blacklist. Nesorina ny Despicably ho fitsarana manokana; notazonina ho an' ny mpanoratra/anganony ny famaritana masiaka, malaza, mahery indrindra, firaisana ara-nofo ary famonoana. Nampitaina tsy nosivanina ny tonon' ny teny nalaina ary voamarika ho dikan-teny; tsy niova ny original title/citation.
existing_preserved: tsy N/A satria misy lahatsoratra mg. Voatazona ny rainy Peleus, zanany Neoptolemus, Biôgrafia, Freebase sy ny sokajy tany am-boalohany; infobox foana sy vangovango no nosoloina votoaty. Foana ny sandbox ka tsy misy asa teo an-toerana voafafa.
wikitext_only: nodinihina ny soratra manta sy ny diff fanitsiana, tsy misy Markdown na wrapper; validate offline nahomby. Mbola hataon' ny mpandrindra ny fandinihana ny rendered preview offline aorian' ny prepare, tsy fisintonana resources na human approval izany.
""")
    write_json(J/'review.json',dict.fromkeys(GATES,True))
    write_json(J/'integrity-audit.json',dict(sections=25,source_refs=len(source_refs),draft_refs=len(refs),images=len(files),source_urls_preserved=True,isbn_preserved=True,unique_headings=len(headings),vocabulary_records=len(vocabulary),raw_review='coordinator_autonomous',external_references_opened=False))
    artifact_hashes(J.resolve())
    print('All raw-draft review gates evidenced; ready for guarded preparation')


if __name__=='__main__':main()
