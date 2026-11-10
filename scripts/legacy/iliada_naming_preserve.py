"""Keep the accepted lead without falsely approving an unfinished naming revision."""
import difflib
from pathlib import Path

import mwparserfromhell as mw

from mgwiki_editor.core import GATES, digest, lint_wikitext, now, read_json, write_json

JOB = Path('runs/iliada-naming-20261106')


def signature(text):
    code = mw.parse(text)
    return {
        'references': [str(t) for t in code.filter_tags()
                       if str(t.tag).lower() in {'ref', 'references', 'nowiki'}],
        'targets': [str(link.title) for link in code.filter_wikilinks()],
        'urls': [str(link.url) for link in code.filter_external_links()],
        'headings': [str(h) for h in code.filter_headings()],
        'categories': [str(link) for link in code.filter_wikilinks()
                       if str(link.title).startswith(':Sokajy:')],
    }


def main():
    state = read_json(JOB / 'job.json')
    plan = read_json(JOB / 'section-plan.json')
    lead = JOB / 'sections/00-lead'
    old = (lead / 'source.wiki').read_text(encoding='utf-8')
    accepted = (lead / 'section.wiki').read_text(encoding='utf-8')
    assert signature(old) == signature(accepted)
    base = state['sandbox']['text']
    assert base.startswith(old)
    draft = accepted + base[len(old):]
    assert signature(base) == signature(draft)
    assert not lint_wikitext(draft)
    assert draft.endswith('\n') == base.endswith('\n')
    (JOB / 'draft.wiki').write_bytes(draft.encode('utf-8'))
    plan[0]['status'] = 'accepted_partial_verified_title_and_names; further_transcription_blocked'
    for section in plan[1:]:
        section['status'] = 'preserved_base; naming_revision_not_completed'
    write_json(JOB / 'section-plan.json', plan)
    write_json(JOB / 'review.json', dict.fromkeys(GATES, False))
    vocabulary = read_json(lead / 'vocabulary.json')
    files = ['user-request.wiki', 'section-plan.json', 'prior-vocabulary.json',
             'prior-review.json', 'prior-proposal.json', 'prior-receipt.json',
             'country-names.json', 'link-map.json', 'source.wiki', 'sandbox.wiki',
             'existing.wiki', 'shared-references.wiki', 'partial-changes.diff',
             'resume-status.json', 'sections/00-lead/section.wiki',
             'sections/00-lead/notes.wiki', 'sections/00-lead/vocabulary.json']
    files += [str(p.relative_to(JOB)) for p in (JOB / 'naming-evidence').glob('*.json')]
    vocabulary[0]['evidence_files'] = sorted(set(vocabulary[0]['evidence_files'] + files))
    write_json(JOB / 'vocabulary.json', vocabulary)
    (JOB / 'partial-changes.diff').write_text(''.join(difflib.unified_diff(
        base.splitlines(True), draft.splitlines(True),
        fromfile='sandbox1153307', tofile='local partial Iliada naming draft')),
        encoding='utf-8')
    write_json(JOB / 'resume-status.json', {
        'recorded_at': now(), 'status': 'blocked_incomplete_naming_revision',
        'destination': state['destination'], 'sandbox_revision': state['sandbox']['revision_id'],
        'source_sha256': state['source']['sha256'], 'draft_sha256': digest(draft.encode('utf-8')),
        'accepted_sections': ['00-lead: verified portion only'],
        'remaining_sections_preserved_from_base': len(plan) - 1,
        'blockers': [
            'French spellings/identities are pinned, but requested further Malagasy '
            'transcriptions for several names are not evidenced; no pronunciation guessed.',
            'Whole-article naming harmonization remains incomplete; all review gates false.',
        ],
        'identity_or_factual_ambiguity_claimed': False,
        'publication_attempted': False, 'prepare_attempted': False,
        'next_action': 'Resolve proper-name transcription evidence, then resume planned '
                       'section-limited edits and whole-article review; retain all existing contributions.',
    })
    with (JOB / 'notes.wiki').open('a', encoding='utf-8') as out:
        out.write("""
== Famakiana sy porofo ==
Novakian' ny mpandrindra manontolo ny source anglisy sy ny sandbox malagasy tamin' ny alalan' ny source-readable.wiki sy sandbox-readable.wiki, izay kopia voafono andalana fotsiny; novakiana koa ny existing.wiki banga. Tsy noheverina ho famakiana feno ireo andalana lava notapahin' ny fitaovana tamin' ny famakiana voalohany, fa nofenoina tamin' ireo kopia voafono. Ny source dia revision 1383771922; ny sandbox revision 1153307 dia mitovy hash amin' ny receipt confirmed teo aloha. Tsy misy local contribution vaovao nesorina. Ny porofo momba ny firenena dia kopia pinned efa eo, ary novakiana offline tamin' ny countries ilay cache iombonana; tsy nisy refresh na fanovana anaram-pirenena.
Nangonina tamin' ny Wiki gateway sy ny request guard iombonana ny fifandraisan' ny anarana anglisy sy frantsay ary ireo pejy malagasy momba azy. Tsy nisy rohy ivelany nosokafana, tsy nisy dictionary endpoint nandika na namoaka fanitsiana. Porofo momba ny maha anarana iray sy ny endriny voasoratra ny langlinks, fa tsy porofo momba ny fanononana na fanoratana malagasy mbola tsy voamarina. Tsy porofo momba ny tsy fisian' ny anarana rehetra ny search tsy nahita valiny.
Hômerôsy revision 1118546 dia manome mazava ny Hômera sy Iliada; Ôdiseosy dia manome Olisy. Azo ampiasaina ireo endrika voaporofo ireo. Tsy nasiana filazana vaovao ao amin' ny lahatsoratra hoe avy mivantana amin' ny fanononana grika ny Iliada: tazonina ho safidin' ny mpampiasa sy anarana efa hita eo an-toerana izany. Tsy voambolana anglisy tsy fantatra ny anarana manokana ka tsy isaina amin' ny fetra 100, ary tsy noforonina ny porofon-dRakibolana.

== Fanakambanana ampahany ==
Neken' ny mpandrindra ny fanitsiana voafetra nataon' ny mpiasa 00-lead rehefa novakiana ny diff sy ny porofo: Iliada no anarana fototra, Iliasy sy Iliady tazonina, Hômera no marika hita maso amin' ny anaran' ilay pôeta. Achille no marika voasoratra efa hita amin' ny pejy malagasy sy frantsay; tsy lazaina fa transcription vaovao malagasy efa voamarina izy io. Tsy novaina ny ref, ny target Hômerôsy na Achille, ny original titles, ny quotations, ny URLs, ny identifiers, ny filenames na ny sokajy. Ny sisa amin' ny sandbox dia natambatra byte-for-byte, tsy novokarina indray. Ny signatures manontolo momba ny references/nowiki, link targets, URLs, headings ary categories dia mitovy amin' ny base. Tafavoaka amin' ny lint offline ny draft ampahany, saingy tsy porofon' ny fahavitan' ny fanitsiana izany.
Fanitsiana ny fanendrena: roa ihany ireo batch anarana ilaina sy voarakitra, en-fr-000.json sy en-fr-045.json. Dison' ny mpandrindra ny nilaza en-fr-090.json tamin' ny mpiasa; tsy lookup tsy nahomby na rakitra very izany, ary tsy miankina aminy ny fanovana nekena.

== Sata voasakana ==
Tsy vita ny fangatahana manerana ny lahatsoratra. Mbola tsy ampy porofo momba ireo transcription malagasy vaovao nangatahina, anisan' izany ny Achille, Hector ary Mycènes; tsy ampy ny endrika frantsay voasoratra irery hanambarana fanononana malagasy vaovao. Tsy ny maha izy azy na ny hevitr' ireo olona sy tanàna no lazaina ho tsy mazava. Tsy noforonina ny endrika vaovao mba hahazoana mandalo ny gate. Mbola samihafa araka ny base teo aloha ny anarana any amin' ny fizarana hafa, ary tsy afaka atao hoe vita ny terminology sy coverage review izany. Voatahiry ny sombiny vita sy ny draft ampahany ary ny drafitra rehetra, ka fanitsiana voatondro ihany no haverina rehefa ampy porofo, fa tsy famoronana lahatsoratra iray manontolo.
False avokoa ny review gates. Tsy natao ny prepare, preview lavitra na publish; tsy nisy fanovana natao tao Wikipedia amin' ity asa ity. Tsy misy human approval foronina, ary tsy misy publication guard nohalefahina. Ny receipt teo aloha dia porofon' ny sandbox taloha ihany fa tsy fanamafisana ny draft vaovao. Ny partial-changes.diff sy resume-status.json no mirakitra ny fanovana eo an-toerana sy ny anton' ny fijanonana.
""")
    print('Preserved partial draft:', JOB / 'draft.wiki')
    print('Unchanged protected metadata; review gates false; no preparation or save.')


if __name__ == '__main__':
    main()
