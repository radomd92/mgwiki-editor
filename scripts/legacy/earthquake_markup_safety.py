"""Small native-markup repairs; no source prose regeneration or network access."""
from pathlib import Path

import mwparserfromhell as mw

JOB = Path('runs/earthquake-20261108')


if __name__ == '__main__':
    text = (JOB/'draft.wiki').read_text(encoding='utf-8')
    text = text.replace('<span id="big one"></span>', '<span id="big_one"></span>')
    code = mw.parse(text)
    changed = []
    for link in code.filter_wikilinks():
        title = str(link.title)
        if title in {'File:significant earthquakes, World, 2024 (cropped).svg',
                     'File:earthquake deaths, World, 2024 (cropped).svg'}:
            raw = str(link.text)
            if raw.startswith('link=|'):
                link.text = raw[len('link=|'):]
                changed.append(title)
    (JOB/'draft.wiki').write_text(str(code), encoding='utf-8')
    with (JOB/'notes.wiki').open('a', encoding='utf-8') as f:
        f.write('\n## Native markup safety\n- Anchor `big_one`: source anchor normalized as MediaWiki does; no invalid whitespace ID.\n- Two OWID static charts: empty `link=` disabled-image-link option removed. Original slider absent; normal File description/attribution access restored. Filenames, captions, order, thumb/upright retained. No image fetched.\n')
    print('Anchor normalized; Commons description access restored for', len(changed), 'static charts.')
