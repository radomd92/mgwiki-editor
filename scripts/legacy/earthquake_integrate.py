"""Coordinator-only integration; keeps metadata and all source citations offline."""
import re
import textwrap
from pathlib import Path

import mwparserfromhell as mw

from genji_en_native import citation as basic_citation, native_templates, param
from mgwiki_editor.core import read_json, write_json

JOB = Path('runs/earthquake-20261108')
COUNTRIES = {
    'China': "Repoblika Entim-Bahoakan' i Sina", 'Sina': "Repoblika Entim-Bahoakan' i Sina",
    'Chile': 'Silia', 'United States': 'Etazonia', 'Canada': 'Kanada', 'Mexico': 'Meksika',
    'Peru': 'Però', 'Philippines': 'Filipina', 'Tajikistan': 'Tajikistàna',
    'Turkey': 'Tiorkia', 'Torkia': 'Tiorkia', 'Haiti': 'Haitỳ',
}


def citation(template):
    """Keep every numbered author, including source's fifteen-author reference."""
    clone = mw.parse(str(template)).filter_templates()[0]
    authors = []
    if clone.has('author'):
        authors.append(str(clone.get('author').value).strip())
        clone.remove('author')
    suffixes = [''] + [str(i) for i in range(1, 101)]
    for suffix in suffixes:
        last = param(clone, 'last'+suffix)
        first = param(clone, 'first'+suffix)
        numbered = param(clone, 'author'+suffix) if suffix else ''
        if last or first:
            authors.append(', '.join(s for s in [last, first] if s))
        elif numbered:
            authors.append(numbered)
        for key in ['last'+suffix, 'first'+suffix] + (['author'+suffix] if suffix else []):
            if clone.has(key):
                clone.remove(key)
    if authors:
        clone.add('author', '; '.join(authors))
    return basic_citation(clone)


def native(text):
    code = mw.parse(text)
    for t in list(code.filter_templates()):
        name = str(t.name).strip().lower()
        if name == 'citation' or name.startswith('cite '):
            replacement = citation(t)
        elif name in {'harvnb', 'harvtxt'}:
            vals = [str(p.value).strip() for p in t.params if str(p.name).strip().isdigit()]
            replacement = '; '.join(vals[:-1])+' ('+vals[-1]+')'
            if param(t, 'p') or param(t, 'pp'):
                replacement += ', p. '+(param(t, 'p') or param(t, 'pp'))
        else:
            continue
        code.replace(t, replacement)
    return native_templates(str(code), {'!': '&#124;'})


def normalize(s):
    parts = re.split(r"(''.*?'')", s, flags=re.S)
    for i in range(0, len(parts), 2):
        for en, mg in sorted(COUNTRIES.items(), key=lambda p: -len(p[0])):
            if en == 'Sina':
                # Avoid replacing the component inside the already correct full country name.
                parts[i] = re.sub(r"(?<! i )(?<!\w)Sina(?!\w)", mg, parts[i])
            else:
                suffix = r'(?! City)' if en == 'Mexico' else ''
                parts[i] = re.sub(r'(?<!\w)'+re.escape(en)+r'(?!\w)'+suffix, mg, parts[i])
        parts[i] = parts[i].replace('ao amin\' i Mars', 'ao amin\' i Marsa')
        parts[i] = parts[i].replace('Ranomasimbe Indianina', 'Ranomasimbe Indiana')
        parts[i] = parts[i].replace('fitsontsorana', 'fitsotsorana')
        parts[i] = parts[i].replace('Fehin\' Afo', 'fehikibon\' afo')
        parts[i] = parts[i].replace('Oseana Pasifika', 'Ranomasimbe Pasifika')
        parts[i] = re.sub(r'(?<=\d),(?=\d{3}(?:\D|$))', ' ', parts[i])
        parts[i] = re.sub(r'(?<=\d)\.(?=\d)', ',', parts[i])
    return ''.join(parts)


def adapt(text, mapping, *, prose=True):
    code = mw.parse(native(text))
    verified = {x['mg'] for x in mapping.values() if x.get('mg')}
    for node in list(code.nodes):
        if isinstance(node, mw.nodes.Text) and prose:
            code.replace(node, normalize(str(node)), recursive=False)
        elif isinstance(node, mw.nodes.Heading) and prose:
            node.title = normalize(str(node.title))
        elif isinstance(node, mw.nodes.Wikilink):
            target = str(node.title).strip()
            if target.lower().startswith(('file:', 'image:')):
                if node.text:
                    node.text = adapt(str(node.text), mapping, prose=prose)
                    # Display parameters are machine syntax, not localized decimal prose.
                    node.text = re.sub(r'\bupright=(\d+),(\d+)', r'upright=\1.\2', str(node.text))
                continue
            label = str(node.text) if node.text is not None else target
            if prose:
                label = normalize(label)
            if target.startswith('#') or target.startswith(':Sokajy:'):
                continue
            base = target.split('#')[0].replace('_', ' ')
            mg = base if base in verified else mapping.get(base, {}).get('mg')
            replacement = (f'[[{mg}|{label}]]' if label != mg else f'[[{mg}]]') if mg else label
            code.replace(node, replacement, recursive=False)
        elif isinstance(node, mw.nodes.Tag) and str(node.tag).lower() not in {'ref', 'references', 'nowiki', 'math'} and node.contents:
            # Original foreign phrases/work titles must not undergo country normalization.
            node.contents = adapt(str(node.contents), mapping,
                                  prose=prose and str(node.tag).lower() != 'i')
    return str(code)


def main():
    plan = read_json(JOB/'section-plan.json')
    mapping = read_json(JOB/'link-map.json')
    pieces = []
    handoffs = []
    vocab = []
    for item in plan:
        directory = Path(item['directory'])
        for filename in ['section.wiki', 'notes.wiki', 'vocabulary.json']:
            if not (directory/filename).is_file():
                raise RuntimeError('Missing section artifact '+str(directory/filename))
        text = (directory/'section.wiki').read_text(encoding='utf-8')
        if not text.strip():
            raise RuntimeError('Empty section '+item['id'])
        if item['id'] == '24-references':
            text = text.replace('== Loharano ==', '== Fanovozan-kevitra ==')
        if item['id'] == '25-bibliography':
            text = text.replace('== Loharano ==', '== Boky sy lahatsoratra nampiasaina ==')
        pieces.append(adapt(text, mapping, prose=item['id'] not in {'25-bibliography', '26-reading'}).strip())
        handoffs.append('\n== '+item['id']+' ==\n'+(directory/'notes.wiki').read_text(encoding='utf-8'))
        records = read_json(directory/'vocabulary.json')
        if isinstance(records, dict):
            records = records.get('terms', records.get('entries', []))
        for record in records:
            evidence = []
            for name in record.get('evidence_files', []):
                path = (directory/name).resolve()
                if path.is_relative_to(JOB.resolve()) and path.is_file():
                    evidence.append(str(path.relative_to(JOB.resolve())))
            record['evidence_files'] = sorted(set(evidence + [str((directory/'source.wiki').relative_to(JOB))]))
            record['section_id'] = item['id']
            vocab.append(record)
        item['status'] = 'integrated_pending_coordinator_review'
    text = '\n\n'.join(pieces)+'\n'
    refs = read_json(JOB/'reference-definitions.json')
    code = mw.parse(text)
    used = {str(tag.get('name').value).strip('\"\' ') for tag in code.filter_tags()
            if str(tag.tag).lower() == 'ref' and tag.has('name')}
    if used - set(refs):
        raise RuntimeError('Unknown reference names '+str(used-set(refs)))
    definitions = [f'<ref name="{name}">'+adapt(refs[name]['body'], mapping, prose=False)+'</ref>'
                   for name in refs if name in used]
    text = text.replace('<references />', '<references>\n'+'\n'.join(definitions)+'\n</references>', 1)
    (JOB/'draft.wiki').write_text(text, encoding='utf-8')
    (JOB/'section-handoffs.wiki').write_text('\n'.join(handoffs), encoding='utf-8')
    write_json(JOB/'integrated-section-plan.json', plan)
    write_json(JOB/'vocabulary.json', vocab)
    (JOB/'draft-readable.txt').write_text('\n'.join('\n'.join(textwrap.wrap(
        line, 150, replace_whitespace=False, drop_whitespace=False,
        break_long_words=False, break_on_hyphens=False)) for line in text.splitlines())+'\n', encoding='utf-8')
    print('Integrated', len(plan), 'sections;', len(vocab), 'vocabulary entries;', len(used), 'refs')
    print('Remaining templates', [str(t.name) for t in mw.parse(text).filter_templates()])


if __name__ == '__main__':
    main()
