"""Resume the pinned job with the user's explicit scope exclusions."""
from pathlib import Path
import shutil
import mwparserfromhell as mw
from mgwiki_editor.core import Wiki, now, read_json, write_json, GuardError

JOB=Path('runs/mahabharata-20261108')


def resume():
    text='''= Fanohizana sy scope neken' ny mpampiasa =
Ny mpampiasa dia namela ny hanesorana ireo filazana mampiahiahy efa nohazavaina. Esorina manontolo ny source.wiki andalana 63 sy 65 sy ny ref :0 rehetra mifandray aminy: Abhijnanashakuntala/Urubhanga ao amin' ny historical references sy ny takela-barahina Sharvanatha. Tsy fanesorana citation fotsiny ka mamela filazana tsy tohanana izany. Ny andalana 61 sy fanazavana momba an' i Panini dia mbola adika. Tsy sakana intsony io scope voafetra io.
Ny filazana tsy misy citation hoe Rashmirathi nahazo Jnanpith tamin' ny 1972 (andalana 347) dia tsy afindra: hita ao amin' ny porofo Wikipedia Ramdhari Singh Dinkar fa Urvashi no mifandray amin' ilay loka. Tehirizina ny fiantraikany sy ny Rashmirathi momba an' i Karna ary ny 1952; tsy manampy resaka Urvashi tsy ilaina.
Ny citation Gaṅgā Rām/Garg simba tao amin' ny 291–292 dia tsy afindra amin' ny filazana Punjabi: ny citation Satnam Singh, The Road to Empire, 2024, pp.200–205 no citation mifanila tohanana ao amin' ny source. Tsy mamorona fanamboarana ny anarana simba na milaza fa novakina ilay boky. Voatahiry ho porofo ny metadata niandohana sy ny tantarany, tsy sakanana amin' ny citation duplicate diso toerana ny fandikana.
Tsy mbola misy preparation na save; draft ampahany teo aloha tazonina. Tsy refetch ny snapshots satria mbola tsy nisy proposal; ny guards no hanamarina fiovan' ny pejy alohan' ny preparation.
== Fomba iombonana ==
Ny worker tsirairay dia mandika fizarana tokana araka ny plan; soratra feno malagasy fa tsy famintinana. Ny lohateny lehibe sy ny subsection dia toy ny source, adika voajanahary. Ny reference definitions ao shared-references.wiki; tsy manao duplicate definition raha reuse ilay source. Atao wikitext tsotra ny unsupported display templates; citation templates tehirizina ho an' ny coordinator. Rohy en voatahiry miaraka amin' ny label malagasy mandra-pampifandraisan' ny coordinator amin' ny target mg voamarina; tsy mamorona target. Ny image filename tsy ovaina; captions sy alt adika. Tsy misy remote access na nested delegation.
Mahābhārata, Bhagavad Gita, Ramayana sy lohateny rehetra sora-mandry. Anarana mpilalao tsy asiana sora-mandry noho ny fiaviany fotsiny. Vyasa/Vyāsa samy source-supported; ampiasaina Vyasa amin' ny fitantarana, tsy ovaina bibliografia. Yudhishthira no fanoratra iombonana fa tsy variants Yudhisthira/Yudhishthara, raha ilay olona iray ihany; tsy ovaina targets sy metadata. Pandava no iombonana amin' ny body; azo tazonina Pāṇḍava amin' ny lead. Jereo ny vocabulary.json iombonana sy evidence/lookup-* ho porofo teny efa misy. BCE=tal. J.K., CE=taor. J.K., efa nitarina tamin' ny lead. India, Pakistàna, Indônezia, Nepaly, Fanjakana Mitambatra araka ny country-names.json; Scotland kosa tsy raisina ho sovereign country avy amin' ilay cache.
Ny angano lazaina mazava ho votoatin' ilay fitantarana sy finoana fa tsy zava-misy ara-tantara na fahamarinan' ny fivavahana. Ny fanavakavahana na fahasembanana ao amin' ny fitantarana dia atao avy amin' ny olona/fitantarana, tsy filazana fa tsy afaka mitondra fanjakana ny jamba amin' ny ankapobeny. Fanazavana voambolana tsy mitovy amin' ny fanampiana doctrine na clinical claim.
'''
    (JOB/'resume-context.wiki').write_text(text,encoding='utf-8')
    with (JOB/'notes.wiki').open('a',encoding='utf-8') as f:
        f.write('\n'+text)
    state=read_json(JOB/'status.json'); state.update(status='in_progress',reason='User-authorized omission of affected claims and citations; translation resumed.',updated_at=now())
    write_json(JOB/'status.json',state)
    plan=read_json(JOB/'section-plan.json')
    for r in plan:
        if r['id']!='00-lead': r['status']='pending'
    write_json(JOB/'section-plan.json',plan)


def metadata():
    wiki=Wiki(); code=mw.parse((JOB/'source.wiki').read_text(encoding='utf-8'))
    d=JOB/'evidence'
    targets={str(l.title).split('#')[0].replace('_',' ').strip() for l in code.filter_wikilinks() if ':' not in str(l.title)}
    tree=mw.parse((d/'kuru-tree.wiki').read_text(encoding='utf-8'))
    targets|={str(l.title).split('#')[0].strip() for l in tree.filter_wikilinks() if ':' not in str(l.title)}
    for t in code.filter_templates():
        if str(t.name).strip().lower() in {'main','see also','further'}:
            targets|={str(p.value).split('#')[0].strip() for p in t.params if str(p.name).strip().isdigit()}
    mapping=read_json(JOB/'link-map.json')
    # Reuse pinned, recent direct topic mappings from earlier related jobs.
    for old in [Path('runs/iliad-en-20261106-r1'),Path('runs/achilles-20261107'),Path('runs/genji-en-20261105-utf8')]:
        p=old/'link-map.json'
        if not p.is_file(): continue
        for k,v in read_json(p).items():
            if k not in targets or mapping.get(k,{}).get('mg') or not v.get('mg'): continue
            src=old/v.get('evidence_file','')
            if not src.is_file(): continue
            dest=d/('reuse-'+old.name+'-'+src.name)
            if not dest.exists(): shutil.copyfile(src,dest)
            mapping[k]=dict(v,evidence_file=str(dest.relative_to(JOB)))
    remaining=sorted(targets-mapping.keys())
    for start in range(0,len(remaining),45):
        p=d/f'body-links-{start:03}.json'
        if not p.is_file():
            data=wiki.site('en').simple_request(action='query',prop='langlinks',titles='|'.join(remaining[start:start+45]),lllang='mg',lllimit='max',formatversion=2).submit()
            write_json(p,dict(retrieved_at=now(),response=data))
        data=read_json(p)['response']
        if 'continue' in data: raise GuardError('Unprocessed link continuation')
        for page in data['query']['pages']:
            mapping[page['title']]=dict(mg=page.get('langlinks',[{}])[0].get('title'),evidence_file=str(p.relative_to(JOB)))
        for n in data['query'].get('normalized',[]):
            if n['to'] in mapping: mapping[n['from']]=mapping[n['to']]
    write_json(JOB/'link-map.json',mapping)
    files=read_json(JOB/'source-image-inventory.json')
    p=d/'all-images.json'
    if not p.is_file():
        data=wiki.site('en').simple_request(action='query',prop='imageinfo',titles='|'.join('File:'+x for x in files),iiprop='timestamp|extmetadata',formatversion=2).submit()
        write_json(p,dict(retrieved_at=now(),response=data))
    p=d/'special-expansions.json'
    templates=[str(t) for t in code.filter_templates() if str(t.name).strip().lower() in {'cite banglapedia','imdb title','librivox book','commons category','wikiquote','wikisource','wikisourcelang'}]
    if not p.is_file():
        text='\n\n'.join(f'EXTRACT {i}\n{t}\nEND EXTRACT {i}' for i,t in enumerate(templates))
        data=wiki.site('en').simple_request(action='expandtemplates',title='Mahabharata',text=text,prop='wikitext',formatversion=2).submit()
        write_json(p,dict(inputs=templates,retrieved_at=now(),response=data))
    mg=sorted({v['mg'] for v in mapping.values() if v.get('mg')})
    p=d/'verified-local-topics.json'
    if not p.is_file():
        data=wiki.site('mg').simple_request(action='query',titles='|'.join(mg),prop='revisions',rvprop='ids|timestamp|content',rvslots='main',formatversion=2).submit()
        write_json(p,dict(retrieved_at=now(),response=data))
    p=d/'category-candidates.json'
    if not p.is_file():
        data=wiki.site('mg').simple_request(action='query',titles='Sokajy:Hindoisma|Sokajy:Literatiora sanskrita|Sokajy:Tononkalo|Sokajy:Literatiora indiana',prop='info',formatversion=2).submit()
        write_json(p,dict(retrieved_at=now(),response=data))
    print('Pinned mappings',len(mapping),'images',len(files),'local topics',len(mg))


if __name__=='__main__':
    import sys
    if 'metadata' in sys.argv: metadata()
    else: resume()
