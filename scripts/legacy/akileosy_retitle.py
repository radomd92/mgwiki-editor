"""Reuse the reviewed Achilles edition for the user's new destination title."""
from pathlib import Path
import shutil
import sys

from mgwiki_editor.core import read_json, write_json, digest

OLD=Path('runs/achilles-20261107')
JOB=Path('runs/akileosy-20261107')


def setup():
    state=read_json(JOB/'job.json');old=read_json(OLD/'job.json')
    assert state['source']['sha256']==old['source']['sha256']
    assert state['existing']['sha256']==old['existing']['sha256']
    assert state['sandbox']['text']==''
    vocab=read_json(OLD/'vocabulary.json')
    for name in ['sections','corrected-sources']:
        shutil.copytree(OLD/name,JOB/name,dirs_exist_ok=True)
    for name in {n for e in vocab for n in e['evidence_files']}:
        src=OLD/name;dest=JOB/name
        if dest.exists():
            assert dest.read_bytes()==src.read_bytes(),name
        else:
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(src,dest)
    for name in ['notes.wiki','review.json','receipt.json','proposal.json','draft.wiki','integrity-audit.json','prepared-review.wiki']:
        shutil.copyfile(OLD/name,JOB/('prior-'+name))
    live=read_json(OLD/'save-reconciliation-snapshot.json')['text']
    (JOB/'prior-observed-save.wiki').write_text(live,encoding='utf-8')
    draft=(OLD/'draft.wiki').read_text(encoding='utf-8')
    lead,body=draft.split('\n== Fiavian\' ny anarana ==',1)
    (JOB/'inherited-body.wiki').write_text("== Fiavian' ny anarana =="+body,encoding='utf-8')
    directory=JOB/'sections/00-title'
    directory.mkdir(parents=True,exist_ok=True)
    (directory/'prior-lead.wiki').write_text(lead,encoding='utf-8')
    (directory/'source.wiki').write_text('\n'.join(state['source']['text'].splitlines()[:27]),encoding='utf-8')
    plan=[]
    for r in read_json(OLD/'corrected-section-plan.json'):
        r=dict(r)
        r['source']=r['source'].replace(str(OLD),str(JOB))
        r['directory']=r['directory'].replace(str(OLD),str(JOB))
        r['status']='inherited_reviewed_unchanged'
        if r['id']=='00-lead':
            r.update(id='00-title',directory=str(directory),status='pending_title_only_revision')
        plan.append(r)
    write_json(JOB/'title-section-plan.json',plan)
    write_json(JOB/'inherited-vocabulary.json',vocab)
    (JOB/'user-title-evidence.wiki').write_text("= Safidin' ny mpampiasa =\nNangataka ny lohateny Akileosy ho an' ny fandikan-teny avy amin' ny Achilles anglisy ny mpampiasa. Lohateny sy anarana fototra ao amin' ny fampidirana ihany no sehatry ny fanovana; Achille dia tazonina ho anarana hafa efa voaporofo amin' ny pejy mg. Tsy lazaina fa voamarina amin' ny rakibolana na tsipelina ofisialy ny Akileosy. Ny toerana avela dia Mpikambana:Bot-Jagwar/Akileosy ihany; tsy atao move, redirect, deletion na fanitsiana mainspace.\n",encoding='utf-8')
    (JOB/'notes.wiki').write_text("""= Fanitsiana ny lohateny ho Akileosy =
== Snapshots sy fampitahana ==
Ny init vaovao dia nametraka ny source Achilles revision1383606011, ny existing Achille revision720907, ary ny sandbox vaovao Mpikambana:Bot-Jagwar/Akileosy izay tsy misy. Mitovy byte amin' ny snapshots efa novakin' ny mpandrindra tao amin' ny asa teo aloha ny source sy ny existing; tsy naverina nalaina na novokarina ny fandikan-teny. Tsy misy mainspace Akileosy araka ny destination-identity.json.
Nohamarinin' ny gateway fa misy ny sandbox Achille taloha amin' ny revision1153340, ary mitovy byte amin' ny prior-observed-save.wiki ny votoatiny. Ny filazan' ny mpampiasa fa tsy hitany dia tsy nampiasaina ho porofo fa tsy nisy ilay pejy. Tsy ovaina na afindra ilay pejy taloha. Ny title-section-plan.json no drafitra vaovao: 00-title ihany no havaozin' ny mpiasa; ny fizarana24 sisa dia tazonina tsy misy fiovana, miaraka amin' ny porofo sy fanamarinana teo aloha.
Ny fampidirana dia mampiasa Akileosy araka ny safidin' ny mpampiasa, ary milaza an' i Achille ho anarana hafa efa nisy. Tazonina ny anarana, original titles, citations, URL, identifiers ary filenames rehetra. Tsy misy fanovana zava-misy na fiheverana vaovao momba ny fanononana/fiavian' ny Akileosy.
== Fitahirizana ny asa efa vita ==
Ny prior-notes.wiki, prior-review.json, section-handoff-notes.wiki ary ny porofo voadika eto no mitahiry ny fandrakofana sary38, refs143, rohy, sokajy sy fanapahan-kevitra ara-piteny teo aloha. Voatazona ny rainy Peleus, zanany Neoptolemus, Biôgrafia, Freebase sy ny sokajy inert amin' ny filaharany. Tsy misy sandbox Akileosy tokony hatambatra. Tsy misy rohy ivelany na sary nosokafana tamin' ity fanovana ity.
Ny drafitra vaovao dia tsy asiana LF farany alohan' ny prepare, mifanaraka amin' ny byte tena voatahiry hitan' ny gateway teo aloha. Safidy amin' ny byte an' ny tolo-panovana vaovao izany, fa tsy fanalefahana ny fampitahana hash: tsy maintsy mitovy tanteraka amin' ny read-back ny drafitra vaovao vao azo lazaina hoe confirmed. Tsy averina alefa ny proposal na receipt taloha.
""",encoding='utf-8')


def merge():
    d=JOB/'sections/00-title'
    lead=(d/'section.wiki').read_text(encoding='utf-8').rstrip('\n')
    assert "'''Akileosy'''" in lead and '|+ Akileosy' in lead
    body=(JOB/'inherited-body.wiki').read_text(encoding='utf-8')
    text=(lead+'\n\n'+body).rstrip('\n')
    assert text.split("== Fiavian' ny anarana ==",1)[1]==(OLD/'draft.wiki').read_text(encoding='utf-8').split("== Fiavian' ny anarana ==",1)[1].rstrip('\n')
    (JOB/'draft.wiki').write_text(text,encoding='utf-8')
    vocab=read_json(JOB/'inherited-vocabulary.json')
    additions=read_json(d/'vocabulary.json')
    for e in additions:
        e['evidence_files']=['user-title-evidence.wiki','sections/00-title/notes.wiki','sections/00-title/source.wiki','sections/00-title/prior-lead.wiki','existing.wiki','destination-identity.json']
    vocab+=additions
    vocab.append(dict(source_term='title-only reuse evidence',source_language='en',domain='editorial provenance',source_sense='reuse of the reviewed article for a newly requested sandbox title',english_definition='The existing reviewed translation is retained; only the displayed lead title and explicit name alias are revised at the user request.',definition_origin='editorial_simple_english',malagasy_definition="Tazonina ilay fandikan-teny efa nodinihina; ny lohateny aseho amin' ny fampidirana sy ny anarana hafa mazava ihany no havaozina araka ny fangatahan' ny mpampiasa.",chosen_expression='Akileosy; Achille ho anarana hafa',status='descriptive',reason='User-requested title, not a claim of dictionary or official naming verification. Entire body retained byte-for-byte except absence of terminal LF in the new exact proposal.',evidence_files=['title-section-plan.json','user-title-evidence.wiki','destination-identity.json','inherited-body.wiki','inherited-vocabulary.json','prior-draft.wiki','prior-notes.wiki','prior-review.json','prior-receipt.json','prior-proposal.json','prior-observed-save.wiki','prior-integrity-audit.json','prior-prepared-review.wiki','sections/00-title/notes.wiki','sections/00-title/section.wiki']))
    write_json(JOB/'vocabulary.json',vocab)
    with (JOB/'notes.wiki').open('a',encoding='utf-8') as f:
        f.write('\n== Fanolorana 00-title ==\n'+(d/'notes.wiki').read_text(encoding='utf-8'))
    print('Merged title-only draft',digest(text.encode()),'terminal LF',text.endswith('\n'))


if __name__=='__main__':
    {'setup':setup,'merge':merge}[sys.argv[1]]()
