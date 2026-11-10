"""Coordinator-only exact integration repairs found during complete raw review."""
import re
import textwrap
from pathlib import Path

import mwparserfromhell as mw

JOB = Path('runs/earthquake-20261108')


def main():
    text = (JOB/'draft.wiki').read_text(encoding='utf-8')
    code = mw.parse(text)
    for link in code.filter_wikilinks():
        if str(link.title).lower().startswith(('file:', 'image:')) and link.text:
            link.text = re.sub(r'\bupright=(\d+),(\d+)', r'upright=\1.\2', str(link.text))
    text = str(code)
    text = text.replace("''Etazonia Geological Survey''", "''United States Geological Survey''")
    text = text.replace('CC BY 4,0', 'CC BY 4.0').replace('andiany 4,0', 'andiany 4.0')
    title = 'Use of relatively located microearthquakes to map fault patterns and estimate the thickness of the brittle crust in Southwest Iceland'
    text = text.replace('"'+title+'"', "''"+title+"''")
    text = text.replace(' A copy can be found at ', " Misy dika ao amin' ny ")
    text = text.replace('Retrieved 30 May 2014.', 'daty nijerena voarakitra: 30 May 2014.')
    text = text.replace(', following Allen (1976), p. 2070, who in turn followed Wood; Gutenberg',
                        ", manaraka an' i Allen (1976), p. 2070, izay nanaraka an' i Wood sy Gutenberg")
    text = text.replace('  See also International Commission', ' Jereo koa International Commission')
    text = text.replace('The Oxford Bible Commentary]', "''The Oxford Bible Commentary'']")
    # Omit an unneeded unsourced explanatory contrast, not a new scientific resolution.
    text = text.replace("no fototr' io mizana io, fa tsy fandrefesana mivantana ny angovo miparitaka amin' ny endriky ny onja.",
                        "no fototr' io mizana io.")
    (JOB/'draft.wiki').write_text(text, encoding='utf-8')
    (JOB/'draft-readable.txt').write_text('\n'.join('\n'.join(textwrap.wrap(line, 145,
        replace_whitespace=False, drop_whitespace=False, break_long_words=False,
        break_on_hyphens=False)) for line in text.splitlines())+'\n', encoding='utf-8')
    with (JOB/'notes.wiki').open('a', encoding='utf-8') as f:
        f.write("\n## Fanamboarana hita tamin’ ny raw review\n- `upright` naverina decimal dot: machine parameters, tsy decimal prose. Filename rehetra tsy niova.\n- `United States Geological Survey` sy `CC BY 4.0` naverina exact: normalization teo aloha tsy tokony nikasika foreign names/identifiers.\n- Papertitle Hjaltadóttir sy boky The Oxford Bible Commentary natao italics; teny/title metadata tsy niova.\n- Citation connectors nadika; dates, authors, URLs, identifiers tsy niova.\n- Nesorina ilay fampitahana fanampiny tsy ilaina momba ny angovo miparitaka ao amin’ ny 12-measurement; source moment-based definition voatazona, tsy namorona famahana adihevitra.\n")
    print('Raw-review machine-parameter/name/licence/citation-rendering repairs retained.')


if __name__ == '__main__':
    main()
