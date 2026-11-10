"""Coordinator integrates accepted omission handoffs; never regenerates article prose."""
import textwrap
from pathlib import Path

import mwparserfromhell as mw

from earthquake_integrate import main as integrate
from mgwiki_editor.core import now, read_json, write_json

JOB = Path('runs/earthquake-20261108')


def main():
    plan = read_json(JOB/'section-plan.json')
    changes = read_json(JOB/'omission-plan.json')
    for change in changes:
        directory = Path(change['directory'])
        for name in ['section.wiki', 'notes.wiki', 'vocabulary.json']:
            if not (directory/name).is_file():
                raise RuntimeError('Missing corrected artifact '+str(directory/name))
        for entry in plan:
            if entry['id'] == change['id']:
                entry['prior_directory'] = entry['directory']
                entry['directory'] = change['directory']
                entry['status'] = 'accepted_targeted_omission_pending_article_review'
        change['status'] = 'accepted_by_coordinator'
    write_json(JOB/'section-plan.json', plan)
    write_json(JOB/'omission-plan.json', changes)
    integrate()
    text = (JOB/'draft.wiki').read_text(encoding='utf-8').replace('{{!}}', '&#124;')
    replacements = {
        "tany [[Shaanxi]], any Repoblika Entim-Bahoakan' i Sina.": 'tany [[Shaanxi]], any Sina.',
        "ka mivoaka ny angovo voatahiry.": "ka mivoaka ny [[Angovon-toerana|angovo voatahiry]].",
        "Ny asa mifandray amin' ny horohoron-tany ao amin' ny faritra iray dia faritana": "Ny fisehoan' ny horohoron-tany ao amin' ny faritra iray dia faritana",
        "isaky ny singam-pandrefesana ny habaka ao amin' io toerana io": "isaky ny ventin-kadiry ao amin' io toerana io",
        "Sampan-draharaha momba ny Fandinihana ny Haibolan-tany any Etazonia": "Sampan-draharaha amerikana momba ny jeôlôjia",
        "Sampan-draharaha momba ny fanadihadiana ara-jeôlôjia any Etazonia": "Sampan-draharaha amerikana momba ny jeôlôjia",
        "injeniera momba ny fanoherana ny horohoron-tany": "injenieria momba ny fiarovana amin' ny horohoron-tany",
        '[[Plinio Zokiny|Pliny the Elder]]': '[[Plinio Zokiny]]',
        "''The Earthquake Observers: Disaster Science From Lisbon to Richter'' (University of Chicago Press; 2012) 348 pages;": "''The Earthquake Observers: Disaster Science From Lisbon to Richter'' (University of Chicago Press; 2012), pejy 348;",
        ' i Namazu.': ' i Namazu (鯰).', ' i Tē-gû.': ' i Tē-gû (地牛).',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Two actual existing local categories, verified by the saved namespace-14 search.
    text = text.rstrip()+"\n\n[[:Sokajy:Horohorontany]]\n[[:Sokajy:Jeolojia]]\n"
    code = mw.parse(text)
    # Preserve definitions only when surviving claims still cite them.
    refs = [t for t in code.filter_tags() if str(t.tag).lower() == 'ref']
    used = {str(t.get('name').value).strip('\"\' ') for t in refs if t.self_closing and t.has('name')}
    for tag in refs:
        if not tag.self_closing and tag.has('name'):
            name = str(tag.get('name').value).strip('\"\' ')
            if name not in used:
                code.remove(tag)
    text = str(code)
    for forbidden in ['IRIS', 'name="Sibson"', 'name="Rudnicki"', 'fivadihan\' ny rano ambanin\' ny tany',
                      "fihenjanana fototra lehibe indrindra dia mitovy"]:
        if forbidden in text:
            raise RuntimeError('Omitted material remains: '+forbidden)
    (JOB/'draft.wiki').write_text(text, encoding='utf-8')
    (JOB/'draft-readable.txt').write_text('\n'.join('\n'.join(textwrap.wrap(
        line, 145, replace_whitespace=False, drop_whitespace=False,
        break_long_words=False, break_on_hyphens=False)) for line in text.splitlines())+'\n', encoding='utf-8')
    with (JOB/'notes.wiki').open('a', encoding='utf-8') as f:
        f.write("\n== Fampidirana ny fanitsiana voafetra ==\nVita ny fampidirana ireo handoffs efatra. Tsy nosoloina ny fizarana 24 hafa. Nesorina ny filazana pressure–vaporization sy ny tsiahy Sibson/Rudnicki tsy ampiasaina intsony; voatazona ny Nur sy ny fanazavana momba ny tsindry, fitsotsorana ary horohoron-tany manaraka. Nesorina ny fanazavana stress–weight, nefa voatazona ny filaharana ara-fihenjanana sy ny fanazavana stress-drop. Nesorina ireo firesahana IRIS roa; tsy noforonina fanitarana. Ny dika taloha dia mbola voatahiry.\nNampiraisina ny fanazavana USGS sy injenieria, ny fisehoan’ ny horohoron-tany ary ny ventin-kadiry; naverina ny rohy Angovon-toerana araka ny source sy ny local langlink. Sina no ilazana ilay toerana ara-tantara tamin’ ny 1556, araka ny local extract sy ny anarana fohy voamarina. Sokajy:Horohorontany sy Sokajy:Jeolojia nampiana any amin’ ny farany ho rohy inert araka ny evidence/category-search.json, fa tsy anarana noforonina.\n")
    write_json(JOB/'status.json', {'status': 'whole_article_review', 'updated_at': now(),
               'user_authorized_omissions': True, 'publish_attempted': False})
    print('User-authorized omissions merged; remaining reference definitions:', len(used))


if __name__ == '__main__':
    main()
