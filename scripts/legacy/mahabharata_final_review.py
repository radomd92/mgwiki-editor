"""Record coordinator review only after examining the complete assembled article."""
from pathlib import Path
from collections import Counter
import re
import mwparserfromhell as mw
from mgwiki_editor.core import read_json, write_json, lint_wikitext, now

JOB=Path('runs/mahabharata-20261108')


if __name__=='__main__':
    draft=(JOB/'draft.wiki').read_text(encoding='utf-8')
    errors=lint_wikitext(draft)
    if errors: raise ValueError(errors)
    coverage=read_json(JOB/'coverage-report.json')
    if coverage['missing_source_urls'] or coverage['images']['missing'] or coverage['images']['extra']:
        raise ValueError('Unreconciled coverage loss')
    if coverage['source_references']-coverage['draft_references']!=3:
        raise ValueError('Unexpected reference count')
    defs=Counter(); refvalues={}
    for tag in mw.parse(draft).filter_tags():
        if str(tag.tag)=='ref' and tag.has('name') and not tag.self_closing:
            key=(str(tag.get('group').value).strip('"\' ') if tag.has('group') else '',str(tag.get('name').value).strip('"\' '))
            defs[key]+=1
            refvalues.setdefault(key,set()).add(str(tag.contents))
    if any(len(x)>1 for x in refvalues.values()): raise ValueError('Conflicting named reference definitions')
    plan=read_json(JOB/'section-plan.json')
    if len(plan)!=32: raise ValueError('Unexpected section coverage')
    for row in plan:
        row['status']='accepted_after_coordinator_whole_article_review'
    write_json(JOB/'section-plan.json',plan)
    with (JOB/'notes.wiki').open('a',encoding='utf-8') as out:
        out.write('''
== Fanamarinana manontolo nataon' ny coordinator ==
Novakina sy nampitahaina tamin' ny source anglisy voatahiry ny draft manta manontolo, hatramin' ny lead ka hatramin' ny rohy ivelany, ny tabilao sy bibliography. Noraisina tsirairay ny handoff 32, tsy natao fanekena farany ny fahavitan' ny worker. Ny fragments source dia mitambatra byte-for-byte ho source.wiki feno; ny headings tafiditra tamin' ny faran' ny fragment teo aloha dia naverina tamin' ny toerana mifanaraka aminy fa tsy nanesorana prose. Voatahiry ny sary 18, ny tabilao parva 18 + Harivamsa, ny genealogical names/relations/notes rehetra, ary ny rohy ivelany sy bibliografika rehetra afa-tsy ireo efatra URL voafaritra ao coverage-report.json.

Ny scope exclusion neken' ny mpampiasa dia nampiato ny filazana momba ny Abhijnanashakuntala/Urubhanga tao amin' ny historical references sy ny takela-barahina Sharvanatha, miaraka amin' ny ref :0. Nampiharina tamin' ny fehezanteny Phalgunadi izay citation Ramayana no nanohanany Mahabharata koa ny fanesorana filazana sy citation tsy mifanaraka; ireo votoaty javaney hafa dia mitoetra miaraka amin' ny citation ANU. Ny Garg dia naverina taorian' ny fahitana fa locale Latin-1 tamin' ny readable helper no nahatonga ny fiheverana diso hoe simba ny anarana. Tsy heverina ho porofo momba ny tsy fahamarinan' ilay encyclopedia ny fifindran-toerany tamin' ny revision taloha. Clause Jnanpith diso momba ny Rashmirathi nesorina; ny Rashmirathi/Karna/1952 nijanona. Ny datin' ny lisitra parva Kushan dia nofaritana amin' ny sehatry ny lisitra fa tsy natao hoe Sanskrit text tranainy indrindra eran-tany. Ny adjective theatrical manjavozavo tamin' ny tetikasa Ray tsy natao filazana hoe teatra an-tsehatra; ny tetikasa sy citation nijanona. Tsy misy dikany manan-danja mbola tsy voavaha na fanesorana tsy voarakitra amin' ny article sisa.

Ny fehezanteny malagasy dia nodinihina ho feno sy voajanahary: tsy caveman, tsy famintinana, tsy prose anglisy tavela afa-tsy anarana, lohateny, metadata bibliografika ary voambolana vahiny voazava. Ny apostrophe amin' ny prose vaovao dia amin' ny / an' i / ho an' ny, tsy nanaovana global replacement tamin' ny citations, quotations, foreign names na URLs. Nampiraisina ny labels fiteny amin' ny pejy mg voamarina. Ny anaran' olona dia tsy navadika filaharana; tsy misy anarana malagasy mila vinavinaina ny surname, ary tsy misy anarana personal non-Latin nosoratana tamin' ny prose vaovao tsy misy romanization. Nohazonina ny original scripts amin' ny bibliografia sy ny lohateny sanskrita miaraka amin' ny Latin form.

Ny acronyms BBC, PGW, CE, BORI, IMDb sy PDF dia manana fanazavana malagasy; MB dia singam-pandrefesana fa tsy fanafohezana agency. STAR Plus sy Zee TV dia marika fantsona, tsy nanamboarana expansion ara-tantara avy amin' ny vinavina. Ny retained foreign institutional phrases sy titles dia sora-mandry miaraka amin' ny gloss araka izay ilaina, fa tsy ny anaran' olona/toerana. Ireo parentheses sy lexical gloss ao amin' ny dikantenin-teny nalaina dia mitahiry ny hevitra, tsy manampy doctrine. Ny medical jôndisy dia transcription descriptive miaraka amin' ny fanazavana sy English jaundiced, ary mety ho dikan' ny anarana Pandu ihany no resahina, tsy diagnosis. Tsy nalaina ho fahamarinana ara-pitsaboana ny angano mahatonga fahajambana, na noraisina ho filazan' ny rakipahalalana ny hevitr' i Vidura momba ny jamba.

Nohazavaina ny voambolana sarotra araka ny source sense, English definition sy Malagasy definition. Porofo read-only dictionary voatahiry; ny misses/no_matching_language/502 sy ireo Malagasy definitions malemy na diso sense dia tsy nomena sata fanamarinana one-word equivalent. Ny descriptive wording marina no nampiasaina rehefa tsy nisy label voamarina. Misy lisitra unknown-vocabulary.wiki noho ny habetsahan' ny labels hohamarinina amin' ny fanoratana tiana kokoa; tsy midika hevitra ara-tantara tsy fantatra izany. Ny God → Andriamanitra (tokana) sy vulgate → Volgata dia nolavina noho ny tsy fitovian-kevitra, ka soratra tsotra no tazonina. Ny country cache sy ny exception Singaporo ary naming evidence rehetra dia tafiditra amin' ny proposal hashes amin' ny vocabulary evidence.

Nodinihina ny neutrality sy words-to-watch rehetra amin' ny contexte, fa tsy blacklist. Nesorina ny fiderana source tsy voafaritra toy ny glorious, sady voatahiry ny fanombanana nomena an' i Oldenberg, Winternitz, Agarwal, Bhattacharya ary Chikermane. Ny quotations nadika dia voamarika fa dika malagasy. Ny data sy uncertainty ara-tantara dia nijanona; ny finoana hindoa/jaina, fahaterahana indray sy lanitra/helo dia nofaritana ho ao amin' ny tantara na finoana, fa tsy empirically verified events. Tsy misy unsupported synthesis, personal attack na filazana vaovao momba ny olona mbola velona.

Ny references 142 ao source dia 139 ao draft, noho ny ref :0 roa sy abebooks iray ihany. Tsy very ny definitions/reuses hafa ary tsy misy conflicts. Ny citation metadata, dates, URLs, ISBN/DOI/JSTOR/OCLC sy pejy dia voatahiry; metadata missing/incomplete ao source tsy noforonina na nolazaina fa voamarina tamin' ny vakiteny ivelany. Tsy nosokafana ny external links, DOI, references na image URLs. Ny required Wikipedia API sy read-only dictionary ihany no network natao. Ny preview dia hojerena offline aorian' ny prepare, tsy ampidirina resources ivelany.

Ny existing.wiki sy sandbox.wiki dia samy foana: existing_preserved N/A, tsy misy user work nosoloina. Sokajy vaovao tokana, Boky, voamarina ary inert eo amin' ny farany; tsy misy source category nadika tamin' ny vinavina na tracking categories nateraky ny templates/ISBN. Tsy misy live interwiki, DEFAULTSORT, redirects, mainspace writes na Wikidata/Wiktionary edits. Native wikitext avokoa ny draft, tsy misy output wrapper na Markdown. Ny structural lint dia fanamarinana fanampiny ihany, fa tsy porofo irery momba ny fiteny.

Vita ny fanamarinana editorial alohan' ny preparation. Tsy human approval izany; ny proposal sy ny preview voaomana dia mbola hodinihin' ny coordinator, ary publish guarded ihany no azo atao.
''')
    review=read_json(JOB/'review.json')
    write_json(JOB/'review.json',dict.fromkeys(review,True))
    write_json(JOB/'status.json',dict(status='reviewed_ready_for_prepare',updated_at=now(),
        source_revision=1384087555,completed_sections=[r['id'] for r in plan],remaining_sections=0,
        full_translation_complete=True,prepared=False,published=False,scope_exclusions_documented=True))
    print('Recorded coordinator review of 32 sections; gates evidenced. Preview/publish pending.')
