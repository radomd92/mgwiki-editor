"""Resolve specific local names and the qahramana source redirect."""
import json
from pathlib import Path

from mgwiki_editor.core import Wiki

J=Path('runs/alina-iraika-20261105')


def main():
    wiki=Wiki()
    data=wiki.site('en').simple_request(action='query',prop='langlinks',
         titles='China|United States',lllang='mg',formatversion=2).submit()
    (J/'extra-country-links.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    data=wiki.site('en').simple_request(action='parse',page='Abbasid harem',prop='sections',formatversion=2).submit()
    (J/'qahramana-sections.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    for row in data['parse']['sections']:
        if row['line']=='Qahramana':
            result=wiki.site('en').simple_request(action='parse',page='Abbasid harem',section=row['index'],prop='wikitext',formatversion=2).submit()
            (J/'qahramana-context.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
