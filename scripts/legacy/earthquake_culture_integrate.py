"""Integrate one accepted final section only; retain previous assembled work."""
from pathlib import Path

from mgwiki_editor.core import read_json, write_json

JOB = Path('runs/earthquake-20261108')


if __name__ == '__main__':
    d = JOB/'sections/20-culture-final'
    text = (JOB/'draft.wiki').read_text(encoding='utf-8')
    start = text.index("== Ao amin' ny kolontsaina ==")
    end = text.index("== Ivelan' ny Tany ==", start)
    fragment = (d/'section.wiki').read_text(encoding='utf-8')
    text = text[:start]+fragment.rstrip()+'\n\n'+text[end:]
    (JOB/'draft.wiki').write_text(text, encoding='utf-8')
    for name in ['section-plan.json', 'integrated-section-plan.json']:
        plan = read_json(JOB/name)
        for item in plan:
            if item['id'] == '20-culture':
                item['prior_directory'] = item['directory']
                item['directory'] = str(d)
                item['status'] = 'accepted_final_fragment'
        write_json(JOB/name, plan)
    with (JOB/'section-handoffs.wiki').open('a', encoding='utf-8') as f:
        f.write('\n\n# 20-culture-final\n'+(d/'notes.wiki').read_text(encoding='utf-8'))
    with (JOB/'notes.wiki').open('a', encoding='utf-8') as f:
        f.write('\n## 20-culture final integration\nOnly accepted fragment replaced. Two films after 2002 omitted under user authorization; citation chronology issue preserved as EQ-S007 / 20-culture-CITE-01. Earlier novels, other culture prose, image, and all ref uses unchanged. Original title The Earthquake in Chile restored, not translated country label.\n')
    print('One accepted culture fragment integrated; all other assembled content retained.')
