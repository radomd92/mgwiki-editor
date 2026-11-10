"""Offline section plan and source viewing copies for the requested naming edit."""
import shutil
import textwrap
from pathlib import Path

from mgwiki_editor.core import read_json, write_json
from iliad_troasy_plan import STARTS

JOB = Path('runs/iliada-naming-20261106')
PRIOR = Path('runs/iliad-troasy-20261106')


def readable(text):
    return '\n'.join('\n'.join(textwrap.wrap(line, 130, break_long_words=False,
                        break_on_hyphens=False, replace_whitespace=False,
                        drop_whitespace=False)) for line in text.split('\n'))


def main():
    state = read_json(JOB / 'job.json')
    receipt = read_json(PRIOR / 'receipt.json')
    assert state['sandbox']['sha256'] == receipt['draft_sha256']
    assert state['sandbox']['revision_id'] == receipt['revision_id']
    assert state['source']['sha256'] == read_json(PRIOR / 'job.json')['source']['sha256']
    base = state['sandbox']['text']
    points = [0 if h is None else base.index(h + '\n') for _, h in STARTS] + [len(base)]
    assert points == sorted(points)
    plan = []
    for index, (sid, heading) in enumerate(STARTS):
        directory = JOB / 'sections' / sid
        directory.mkdir(parents=True, exist_ok=True)
        fragment = base[points[index]:points[index + 1]]
        (directory / 'source.wiki').write_text(fragment, encoding='utf-8')
        (directory / 'source-readable.wiki').write_text(readable(fragment), encoding='utf-8')
        shutil.copyfile(PRIOR / 'sections' / sid / 'source-en.wiki', directory / 'source-en.wiki')
        plan.append({'id': sid, 'heading': heading or 'lead/infobox',
                     'directory': str(directory), 'status': 'pending',
                     'dependencies': 'Name map and shared references; all metadata protected.'})
    write_json(JOB / 'section-plan.json', plan)
    assert ''.join((JOB / 'sections' / r['id'] / 'source.wiki').read_text(encoding='utf-8') for r in plan) == base
    for name in ('source', 'sandbox', 'existing'):
        (JOB / (name + '-readable.wiki')).write_text(readable(state[name]['text']), encoding='utf-8')
    for name in ('country-names.json', 'link-map.json', 'shared-references.wiki'):
        shutil.copyfile(PRIOR / name, JOB / name)
    for name in ('receipt.json', 'review.json', 'vocabulary.json', 'proposal.json'):
        shutil.copyfile(PRIOR / name, JOB / ('prior-' + name))
    (JOB / 'user-request.wiki').write_text("= Fangatahana =\nin the iliad article in progress here: i think iliada is a better transcription as it follows ancient greek. iliasy can be kept. use malagasy transcription of the french translation, for proper nouns\n\n= Scope =\nIliada no anarana fototra; Iliasy no anarana hafa. Anarana grika ao amin’ ny fitantarana no ampifanarahana amin’ ny endriny frantsay, fa tsy anaran’ ny mpikaroka sy mpandika teny ankehitriny. Troasy efa nangatahana dia tazonina. Tsy ovaina ny original titles, citation metadata, quotations, URLs, identifiers, filenames, targets ary categories. Tsy misy page move.\n", encoding='utf-8')
    (JOB / 'notes.wiki').write_text("= Fanitsiana ny anarana =\nSandbox efa misy no base, revision 1153307; voamarina fa mitovy tanteraka amin’ ny draft voatahiry teo aloha. Mainspace Iliasy banga. Tsy ampiasaina ho base ilay job Iliada banga teo aloha. Mitovy ny source anglisy revision 1383771922. Tazonina ny contributions/references/images/links/categories rehetra.\n\n== Drafitra isam-pizarana ==\n" + '\n'.join('* ' + r['id'] + ': ' + r['heading'] + '; ' + r['directory'] + '; pending.' for r in plan) + '\n', encoding='utf-8')
    for name in ('source', 'sandbox'):
        print(name, len((JOB / (name + '-readable.wiki')).read_text().splitlines()))


if __name__ == '__main__':
    main()
