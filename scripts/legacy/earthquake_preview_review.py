"""Read prepared HTML offline; extract complete text and structural metadata."""
import re
import argparse
import textwrap
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

from mgwiki_editor.core import artifact_hashes, digest, read_json, write_json

JOB = Path('runs/earthquake-20261108')


class OfflinePreview(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []
        self.ids = []
        self.links = []
        self.images = []
        self.headings = []
        self.editsection_depth = 0
        self.depth = 0
        self.current_heading = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        void = tag in {'img', 'br', 'hr', 'meta', 'link', 'input', 'wbr', 'source'}
        if not void:
            self.depth += 1
        if 'mw-editsection' in attrs.get('class', '').split() and not self.editsection_depth:
            self.editsection_depth = self.depth
        if attrs.get('id'):
            self.ids.append(attrs['id'])
        if tag == 'a':
            self.links.append(attrs)
        if tag == 'img':
            self.images.append(attrs)
        if tag in {'h2', 'h3', 'h4', 'h5', 'h6'}:
            self.current_heading = [tag, attrs.get('id'), '']
        if tag in {'p', 'div', 'li', 'br', 'figure', 'figcaption', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            self.text.append('\n')

    def handle_endtag(self, tag):
        if self.current_heading and tag == self.current_heading[0]:
            self.headings.append(self.current_heading)
            self.current_heading = None
        if tag in {'p', 'li', 'figcaption', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            self.text.append('\n')
        if self.editsection_depth == self.depth:
            self.editsection_depth = 0
        self.depth -= 1

    def handle_data(self, data):
        if not self.editsection_depth:
            self.text.append(data)
            if self.current_heading:
                self.current_heading[2] += data


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--job', type=Path, default=JOB)
    JOB = parser.parse_args().job
    proposal = read_json(JOB/'proposal.json')
    html = (JOB/'preview.html').read_text(encoding='utf-8')
    preview = OfflinePreview()
    preview.feed(html)
    ids = set(preview.ids)
    broken = sorted({unquote(x['href'][1:]) for x in preview.links if x.get('href', '').startswith('#')
                     and unquote(x['href'][1:]) not in ids})
    duplicate_ids = [k for k, v in Counter(preview.ids).items() if v > 1]
    missing_files = [x for x in preview.links if 'new' in x.get('class', '').split()
                     and 'Sary' in x.get('href', '')]
    assert not broken, broken
    assert not duplicate_ids, duplicate_ids
    assert not missing_files, missing_files
    assert len(preview.images) == 17
    assert len(preview.headings) == 46
    assert artifact_hashes(JOB.resolve()) == proposal['artifacts']
    assert digest(html.encode()) == proposal['preview_sha256']
    text = ''.join(preview.text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    lines = []
    for line in text.splitlines():
        lines.extend(textwrap.wrap(line.strip(), 150, break_long_words=False, break_on_hyphens=False) or [''])
    (JOB/'preview-readable.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    write_json(JOB/'preview-structure.json', {
        'mode': 'offline HTML only; no linked resources opened', 'proposal_digest': proposal['digest'],
        'headings': preview.headings, 'image_elements': preview.images,
        'broken_internal_fragments': broken, 'duplicate_ids': duplicate_ids,
        'missing_file_links': missing_files, 'links': preview.links,
    })
    print('Offline preview:',len(preview.headings),'headings;',len(preview.images),'images;',len(lines),'complete text lines; fragment/file checks passed.')
