"""Preserve prior draft and assign only user-authorized local section corrections."""
import shutil
from pathlib import Path

from mgwiki_editor.core import now, read_json, write_json

JOB = Path('runs/earthquake-20261108')
ASSIGNMENTS = {
    '03-faults': 'Remove ONLY the simplified principal-stress/weight explanation from Azo hazavaina through Eo anelanelan ireo karazana roa ireo. Preserve sourced stress hierarchy before it and stress-drop/energy conclusion after it. Do not replace with guessed physics.',
    '07-rupture': 'Remove ONLY first sentence of pore-pressure subsection claiming heat raises pressure and consequently vaporization, and its Sibson/Rudnicki ref tokens. Preserve later supported pressure/slip/aftershock discussion; repair dangling anaphora without adding facts. Keep every image and remaining ref.',
    '22-related': 'Remove ONLY IRIS Consortium list entry, whose expansion has no pinned evidence. Preserve every other topic, acronym gloss and source link target. No invented IRIS expansion.',
    '27-external': 'Remove ONLY IRIS seismic monitor entry and URL; preserve USGS and Wikivoyage links exact, and existing justified wrapper omissions.',
}


def main():
    backup = JOB/'before-user-authorized-omissions'
    backup.mkdir(exist_ok=False)
    for name in ['draft.wiki', 'vocabulary.json', 'review.json', 'notes.wiki', 'status.json',
                 'integrated-section-plan.json']:
        shutil.copyfile(JOB/name, backup/name)
    plan = read_json(JOB/'section-plan.json')
    corrections = []
    for sid, task in ASSIGNMENTS.items():
        original = JOB/'sections'/sid
        directory = JOB/'sections'/(sid+'-omit')
        directory.mkdir()
        for name in ['source.wiki', 'readable-source.txt', 'translation-source.wiki']:
            shutil.copyfile(original/name, directory/name)
        shutil.copyfile(original/'section.wiki', directory/'base-section.wiki')
        shutil.copyfile(original/'notes.wiki', directory/'base-notes.wiki')
        shutil.copyfile(original/'vocabulary.json', directory/'base-vocabulary.json')
        write_json(directory/'assignment.json', {'section_id': sid, 'task': task,
                   'output_directory': str(directory), 'status': 'pending'})
        corrections.append({'id': sid, 'directory': str(directory), 'task': task, 'status': 'pending'})
    write_json(JOB/'omission-plan.json', corrections)
    with (JOB/'notes.wiki').open('a', encoding='utf-8') as f:
        f.write('\n== Fangatahana vaovao: fanesorana voafetra ==\nNy mpampiasa nangataka tsy hampiditra ireo soratra mety misy olana ao amin’ ny lahatsoratra havoaka. Ity no manolo ny toromarika taloha hitazona azy rehetra: esorina ireo andalana ara-fizika roa mampisalasala sy ireo firesahana IRIS roa tsy ampy porofo; tsy esorina ny fizarana hafa. Voatahiry ao amin’ ny before-user-authorized-omissions ny dika sy ny porofo teo aloha. Tsy nanafoana vavahady fanamarinana na nanome alalana hanokatra external URLs izany fangatahana izany.\n')
        for item in corrections:
            f.write('* '+item['id']+': '+item['task']+'; '+item['directory']+'; pending.\n')
    write_json(JOB/'status.json', {'status': 'targeted_revision', 'updated_at': now(),
               'user_authorized_omissions': True, 'publish_attempted': False})
    print('Prepared four targeted assignments; original fragments/draft retained.', len(plan), 'sections remain planned.')


if __name__ == '__main__':
    main()
