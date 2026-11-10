"""Assemble completed fragments, without attesting editorial gates."""
import json
from pathlib import Path

import mwparserfromhell as mw

JOB = Path('runs/oedipus-20261105')


def main():
    plan = json.loads((JOB / 'section-plan.json').read_text(encoding='utf-8'))
    sections, notes, vocab = [], [], []
    for record in plan:
        folder = Path(record['directory'])
        for filename in ['section.wiki', 'notes.wiki', 'vocabulary.json']:
            if not (folder / filename).exists():
                raise RuntimeError(f'Missing section artifact: {folder / filename}')
        sections.append((folder / 'section.wiki').read_text(encoding='utf-8').strip())
        notes.append('\n== ' + record['id'] + ' ==\n' + (folder / 'notes.wiki').read_text(encoding='utf-8'))
        entries = json.loads((folder / 'vocabulary.json').read_text(encoding='utf-8'))
        if not isinstance(entries, list):
            raise RuntimeError(f'Invalid section vocabulary: {folder}')
        for entry in entries:
            for name in entry.get('evidence_files', []):
                if not (JOB / name).is_file():
                    raise RuntimeError(f'Missing vocabulary evidence: {name}')
            vocab.append(entry)
        record['status'] = 'assembled_pending_coordinator_review'
    text = '\n\n'.join(sections) + '\n'
    category = '[[:Sokajy:Angano grika]]'
    if category not in text:
        text += category + '\n'
    (JOB / 'draft.wiki').write_text(text, encoding='utf-8')
    (JOB / 'section-notes.wiki').write_text('\n'.join(notes), encoding='utf-8')
    (JOB / 'section-vocabulary.json').write_text(json.dumps(vocab, ensure_ascii=False, indent=2), encoding='utf-8')
    (JOB / 'section-plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    source = (JOB / 'source.wiki').read_text(encoding='utf-8')
    source_code, draft_code = mw.parse(source), mw.parse(text)
    refs_source = [str(t) for t in source_code.filter_tags() if str(t.tag).lower() == 'ref']
    refs_draft = [str(t) for t in draft_code.filter_tags() if str(t.tag).lower() == 'ref']
    report = {
        'source_ref_count': len(refs_source), 'draft_ref_count': len(refs_draft),
        'draft_templates': [str(x.name) for x in draft_code.filter_templates()],
        'source_external_links': [str(x.url) for x in source_code.filter_external_links()],
        'draft_external_links': [str(x.url) for x in draft_code.filter_external_links()],
        'draft_links': [str(x.title) for x in draft_code.filter_wikilinks()],
        'draft_characters': len(text),
    }
    (JOB / 'assembly-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Assembled', len(sections), 'sections;', len(text), 'characters;', len(vocab), 'vocabulary records')


if __name__ == '__main__':
    main()
