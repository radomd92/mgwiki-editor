"""Read only title evidence via guarded Wikipedia gateway."""
from pathlib import Path
from mgwiki_editor.core import Wiki, write_json

def main():
    wiki = Wiki()
    data = wiki.site('en').simple_request(action='query', prop='langlinks', titles='Iliad', lllang='mg', lllimit='max', formatversion=2).submit()
    write_json(Path('/tmp/opencode/iliad-langlink.json'), data)
    print(data)
    data = wiki.site('mg').simple_request(action='query', list='search', srsearch='Iliasy OR Iliady OR Iliade', srnamespace=0, srlimit=20, formatversion=2).submit()
    write_json(Path('/tmp/opencode/iliad-title-search.json'), data)
    print(data)

if __name__ == '__main__':
    main()
