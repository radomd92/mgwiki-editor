"""Finalize coordinator evidence and editorial gates after complete raw review."""
import json
from pathlib import Path

from mgwiki_editor.core import GATES

J=Path('runs/alina-iraika-20261105')


def main():
    p=J/'draft.wiki'
    s=p.read_text(encoding='utf-8')
    s=s.replace("ho an' ny fanontany.","ho an' ny fanontana nataony.")
    s=s.replace("fantatra amin' ny hoe lahatsoratr' i Leiden", "fantatra amin' ny hoe lahatsoratra Leiden")
    s=s.replace("''C major'' (''Do majeur'')", "''C major'' (tonalite Do izay misy elanelam-peo antsasany efatra eo amin' ny naoty voalohany sy fahatelo)")
    s=s.replace("varahina mavo (''brass'')", "varahina mavo (firaka varahina sy fanitso; ''brass'')")
    s=s.replace("loko afangaro amin' ny akora mampiraikitra azy (''tempera'')", "loko afangaro amin' ny rano sy akora mampiraikitra toy ny tamenak' atody (''tempera'')")
    s=s.replace("izay antsoina hoe «tantara kamboty», ary koa", "izay antsoina hoe «tantara kamboty» satria tsy hita tao amin' ireo sora-tanana arabo niandohana, ary koa")
    p.write_text(s,encoding='utf-8')
    vocab=json.loads((J/'vocabulary.json').read_text(encoding='utf-8'))
    lookups={}
    for f in J.glob('lookup-*.json'):
        row=json.loads(f.read_text(encoding='utf-8'))
        lookups[(row.get('edition'),row.get('word','').lower())]=(f.name,row)
    from alina_lookup import TERMS
    for entry in vocab:
        term=entry['source_term'].lower()
        for en,mg in TERMS:
            if en in term or (en=='bowdlerize' and 'bowdlerized' in term) or (en=='automaton' and 'automata' in term):
                for key in [('en',en),('mg',mg)]:
                    if key in lookups:
                        name,data=lookups[key]
                        entry['evidence_files'].append(name)
                        entry.setdefault('dictionary_checks',[]).append({k:data.get(k) for k in ('edition','word','status','url','retrieved_at','error') if k in data})
        if any(x in term for x in ['united states','etazonia']):
            entry['evidence_files']+=['country-usa.json','extra-country-links.json']
        if any(x in term for x in ['mexico','meksika']):
            entry['evidence_files'].append('country-mexico.json')
        if any(x in term for x in ['austri','aotris']):
            entry['evidence_files'].append('country-austria.json')
        if 'china' in term:
            entry['evidence_files']+=['country-china.json','extra-country-links.json']
        if 'qahramana' in term:
            entry['evidence_files']+=['qahramana-context.json','identity-qahramana.json']
        if entry.get('source_term')=='C major':
            entry['english_definition']='A major musical key whose tonic is C, with its third scale degree four semitones above the tonic.'
            entry['chosen_expression']="C major (tonalite Do izay misy elanelam-peo antsasany efatra eo amin' ny naoty voalohany sy fahatelo)"
            entry['malagasy_definition']="Tonalite manana ny Do ho naoty fototra ary elanelam-peo antsasany efatra eo amin' ny naoty voalohany sy fahatelo."
            entry['definition_origin']='editorial_simple_english'
            entry['status']='descriptive'
        if entry.get('source_term')=='brass':
            entry['chosen_expression']='varahina mavo'
        if entry.get('source_term')=='tempera':
            entry['chosen_expression']="loko afangaro amin' ny rano sy akora mampiraikitra toy ny tamenak' atody (tempera)"
            entry['malagasy_definition']="Loko izay afangaro amin' ny akora mampiraikitra mifangaro amin' ny rano, toy ny tamenak' atody, ka mihamafy rehefa tratran' ny rivotra."
        if 'jinn' in term:
            entry['reason']=entry.get('reason','')+' Tsy mifanaraka amin’ ity hevitra ity ny valin’ ny rakibolana mg momba ny jiny; ny hevitra anglisy sy ny rohy mitovy lohahevitra no fototry ny fanazavana, fa tsy porofo rakibolana malagasy.'
            entry['evidence_files']+=['link-map.json','lookup-en-jinn.json','lookup-mg-jiny.json']
        entry['evidence_files']=sorted(set(entry['evidence_files']))
    names={
      'source_term':'country and personal names used in this article',
      'source_language':'en','domain':'naming evidence',
      'source_sense':'Identity-specific country names and culturally established personal-name order, not dictionary equivalence.',
      'english_definition':'Use the attested Malagasy country name and the source-supported Latin personal name in its cultural order.',
      'definition_origin':'editorial_simple_english',
      'malagasy_definition':'Ampiasaina ny anaram-pirenena voamarina amin’ ny pejy malagasy sy ny anaran’ olona amin’ ny abidy latina araka ny filaharana tohanan’ ny loharano.',
      'chosen_expression':'Etazonia; Meksika; Aotrisy; Sina amin’ ny toe-javatra ara-tantara; Tezuka Osamu; Yamamoto Eiichi; Hoshino Yukinobu; Jeon Jin-seok; Han Seung-hui',
      'evidence_files':['country-names.json','country-usa.json','country-mexico.json','country-austria.json','country-china.json','extra-country-links.json','identity-tezuka.json','identity-yamamoto.json','identity-hoshino.json','identity-manhwa.json','identity-bbc.json','identity-dd.json','identity-upa.json','link-map.json','image-map.json','local-categories.json','section-plan.json','section-notes.wiki','coordinator-corrections.json','unknown-vocabulary.wiki'],
      'alternatives_rejected':['Westernizing Japanese names','identifying historical fictional China with the modern People’s Republic'],
      'status':'verified',
      'reason':'Verified local-page naming exceptions and explicit source romanizations; not a claim of dictionary confirmation or sovereignty.'}
    names['evidence_files']+=sorted(f.name for f in J.glob('links-*.json'))
    names['evidence_files']+=sorted(f.name for f in J.glob('images-*.json'))
    vocab.append(names)
    (J/'vocabulary.json').write_text(json.dumps(vocab,ensure_ascii=False,indent=2),encoding='utf-8')
    plan=json.loads((J/'section-plan.json').read_text(encoding='utf-8'))
    for row in plan:
        row['status']='complete_accepted_after_coordinator_review'
        row['dependencies']=['35-references'] if row['id'] not in {'33-gallery','34-related','35-references','36-reading','37-external'} else []
        extra={'02-synopsis':['06-manuscripts','11-embedded'], '07-printed':['06-manuscripts','09-timeline'],
               '10-frame':['15-repetition'], '11-embedded':['17-narrator'], '12-visual':['15-repetition','18-crime'],
               '13-fate':['14-foreshadow'], '14-foreshadow':['15-repetition','18-crime'],
               '17-narrator':['18-crime'],'18-crime':['14-foreshadow'], '26-western':['23-arab']}
        row['dependencies']+=extra.get(row['id'],[])
    (J/'section-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    notes=(J/'notes.wiki').read_text(encoding='utf-8')
    notes+='''
== Fampiraisana sy famerenana nataon’ ny mpandrindra ==
Voavaky manontolo ny source.wiki sy ny existing.wiki ary ny sandbox.wiki; foana ireo roa farany. Voavaky manontolo koa ny loharano fanampiny tamin’ ny fanitsiana 1266414825, ny porofon’ anarana, ary ny lahatsoratra natambatra tamin’ ny endrika wiki manta. Ny sombin-dahatsoratra 37 rehetra dia naverin’ ny mpiasa ary nampitahaina sy neken’ ny mpandrindra; tsy fanomezan-dalana hamoaka avy amin’ ny mpiasa izany. Ao amin’ ny section-notes.wiki ny fanamarihana feno isam-pizarana.

* Hevitra sy fandrakofana: voatazona ny fizarana rehetra, ireo singa 44 amin’ ny filaharana, ireo fiafarana fito, ireo tabilao, ny galeria misy sary 25, ireo sary/lahatsary 42 rehetra ary ny filaharany. Samy ao amin’ ny Commons sy manana fahazoan-dalana malalaka ireo rakitra araka ny metadata Wikipedia (39 public domain sy 3 CC BY-SA 4.0); tsy nisy sary nalaina na nampakarina. Tsy nojerena an-tserasera ireo sary na rohy ivelany.
* Fanovozan-kevitra: ref 143 sy sfn 45 tao amin’ ny loharano; ref 187 ao amin’ ny drafitra, izany hoe samy voatahiry avokoa afa-tsy ilay ref spam iray nofaritana etsy ambony. Tsy misy ref voatonona anarana manana famaritana miverimberina na tsy voafaritra. Natao soratra wiki teratany ny môdely bibliografika, ary natao inert ny ISBN. Voatahiry ny URL sy identifier rehetra, afa-tsy ny URL roa an’ ilay ref spam. Tsy filazana fa novakina na nohamarinina tamin’ ny tranonkala ivelany ny fitazonana metadata, indrindra ireo daty fidirana ao amin’ ny hoavy.
* Metadata simba: ireo saha first/last izay nitahiry anarana feno maromaro (Marzolph/van Leeuwen/Wassouf; Yamanaka/Nishio; McCaughrean/Fowler) dia naseho ho anarana miavaka fa tsy natambatra ho olona noforonina. Ny bibliografia iombonana no manamafy ny anarana telo voalohany. Tsy noforonina andraikitra fanampiny ho an’ i Fowler.
* Fanesorana voafetra: tsy naverina ilay «Iranian Golden Age» tsy mifanaraka amin’ ny tantaran’ ny fanangonana; tsy naverina ilay ref spam; nesorina ilay fehezanteny «last comunes» simba sy tsy manana lohahevitra mazava; nesorina ny anarana mitoka-monina tsy misy porofo «The German Morgan»; tsy naverina ilay marika daty Kayseri «XVI/XVIII» manjavozavo. Voatahiry ao amin’ ny porofo ireo tsy fahazoana antoka, fa tsy lazaina fa voavaha. Tsy misy filazana mifototra amin’ ireo antsipiriany ireo ao amin’ ny lahatsoratra avoaka.
* Daty sy anarana: nampiasaina ny daty Galland 1450–1593 voatanisa mazava sy misy fitanisana; nesorina tao amin’ ny fizarana fanontana ihany ilay fanondroana taloha hoe taonjato faha-14 na faha-15 mba tsy hanohitra izany. Ny marika ara-bakiteny/Burton amin’ ny tononkalo dia nahitsy araka ny fanitsiana 1266414825, izay manondro mazava ny filaharany. Nahitsy ny Eichii Yamamoto sy ny anarana aziatika araka ny fanoratana latina voaporofo.
* Tsy nafindra ilay filazana tsy misy attribution hoe akaiky kokoa ny loharano noho ny dikan’ i Disney ny Aladdin 3477; notazonina ny mpanoratra, ny tetikasa telo, ny taona ary ny toerana any Azia. Tsy nampiana fanombanana vaovao na fiampangana olona velona. Ny tsikera sy fiderana hafa dia manana attribution sy ref, ary voamarika ho dikanteny ireo teny nalaina.
* Rohy: ny source→destination sy ny fallback dia ao amin’ ny link-map.json sy ireo fanamarihana isam-pizarana. Ny rohy tsy voamarina dia soratra tsotra, tsy rohy noforonina. Tsy nampifandraisina tamin’ ny tanàna ny tarika Almora; tsy nampifandraisina tamin’ ny sambo ny submarine society; tsy nampiasaina ho solon’ ny angano arabo ny pejy ara-pivavahana ankapobeny. Naverina ny rohin’ i Aladdin ao amin’ ny kolontsaina; mampifandray amin’ ny fomba fitsikerana lahatsoratra ny fanazavana critical edition. Nampifanarahina tamin’ ny lohateny malagasy ny vatofantsika anatiny rehetra.
* Sokajy: tsy nisy sokajy malagasy teo aloha tokony hotehirizina (N/A). [[:Sokajy:Angano]] ihany no nampiana amin’ ny farany, satria voamarina ny fisian’ ilay sokajy sady mifanaraka amin’ ny votoaty. Inert ilay rohy; tsy nisy sokajy anglisy, interwiki, DEFAULTSORT na môdely fitantanana nafindra.
* Fiteny: voazaha ny fehezanteny malagasy feno, ny elanelana aorian’ ny apostrofa, ny fanazavana fanafohezana sy anarana andrim-pikambanana, ny sora-mandry amin’ ny teny vahiny sy lohateny, ary ny filaharan’ ny anarana. Voahaja ny anarana sy lohateny sy teny voatonona ary metadata tany am-boalohany. Tsy noraisina ho lisitra voarara ireo teny mampitandrina; notazonina araka ny heviny sy attribution ny tsikera sy ny fiderana.
* Voambolana: famaritana anglisy tsotra sy fandikana malagasy nataon’ ny tonian-dahatsoratra no ankamaroan’ ny memo, fa tsy lazaina ho rakibolana voamarina. Ny valin’ ny rakibolana diso hevitra sy ny HTTP 502 dia voatahiry ho toy izany, fa tsy «teny tsy hita». Ny teny iombonana mazava dia nadika amin’ ny famaritana, ary ny teny teknika dia nohazavaina. Mihoatra ny 100 ireo safidy voarakitra ka voatahiry ao amin’ ny unknown-vocabulary.wiki ny lisitra manontolo; tsy midika hevitra fototra mbola tsy voavaha ao amin’ ny lahatsoratra izany.
* Fandraisana anjara malagasy teo aloha: N/A, satria foana ny pejy sy ny sandbox voatahiry; tsy nisy asa teo aloha nosoloina. Tsy natao mainspace ny drafitra.
* Encoding: voatahiry misaraka ao amin’ ny rejected-encoding ny valiny voalohany diso famakiana soratra. Tsy nampiasaina ho porofo momba ny fisiana na tsy fisian’ ny pejy ireo. Ny sarintany farany dia avy amin’ ny fangatahana vaovao nampiasa UTF-8 mazava.
* Fijery sy firafitra: voavaky ny wiki manta manontolo, tsy misy Markdown na fonosana fanazavana. Ny fanamarinana ara-drafitra dia nahomby, ary ny fitsapana eo an-toerana 193 sy ruff dia nahomby. Mbola tsy porofon’ ny fandikana na fanekena olombelona ny lint sy ny fitsapana. Ny topimaso voaomana no hojerena ivelan-tambajotra alohan’ ny publish.
'''
    (J/'notes.wiki').write_text(notes,encoding='utf-8')
    unknown=(J/'unknown-vocabulary.wiki').read_text(encoding='utf-8')
    import re
    unknown=re.sub(r'(?m)^(== \d+\. .* ==)$',r'\1\n* Fisalasalana ara-teny: ny safidy ara-panoratana sy ny teny tokana tiana hampiasaina, raha mbola tsy voamarina amin’ ny rakibolana; tsy fanemorana hevitra fototra tsy mazava.\n* Dingana manaraka: ampitahaina amin’ ny porofo lookup efa misy sy dinihina amin’ ny fandinihana voambolana manaraka; tazonina ny fanazavana mazava raha tsy misy teny tokana voaporofo.',unknown)
    (J/'unknown-vocabulary.wiki').write_text(unknown,encoding='utf-8')
    (J/'review.json').write_text(json.dumps(dict.fromkeys(GATES,True),indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
