"""Rebuild the respiratory-system draft from assembly and apply reviewed cleanup."""
import json
import re
from pathlib import Path

JOB = Path('runs/biology-health-20261110/respiratory-system')
t = (JOB / 'assembly' / 'draft.wiki').read_text(encoding='utf-8')

m = json.loads((JOB / 'link-map.json').read_text(encoding='utf-8'))
verified = {}
for key, val in m.items():
    if val.get('mg'):
        verified[key.split('#')[0]] = val['mg']
verified.update({'Bibikely': 'Bibikely', 'Arthropoda': 'Arthropoda',
                 'Fôtôsentezy': 'Fôtôsentezy', 'trondro': 'Trondro', 'Trondro': 'Trondro'})
mgset = set(verified.values())


def top_links(s):
    res, i = [], 0
    while True:
        a = s.find('[[', i)
        if a < 0:
            break
        depth, j = 0, a
        while j < len(s) - 1:
            if s[j:j + 2] == '[[':
                depth += 1
                j += 2
                continue
            if s[j:j + 2] == ']]':
                depth -= 1
                j += 2
                if depth == 0:
                    break
                continue
            j += 1
        res.append((a, j))
        i = j
    return res


def transform(s):
    out, last = [], 0
    for a, b in top_links(s):
        out.append(s[last:a])
        inner = s[a + 2:b - 2]
        depth, cut = 0, None
        for k, ch in enumerate(inner):
            if inner[k:k + 2] == '[[':
                depth += 1
            elif inner[k:k + 2] == ']]':
                depth -= 1
            elif ch == '|' and depth == 0:
                cut = k
                break
        target = (inner if cut is None else inner[:cut]).strip()
        label = None if cut is None else inner[cut + 1:]
        low = target.lower()
        if low.startswith(('file:', 'image:')):
            if label is not None:
                out.append('[[%s|%s]]' % (target, transform(label)))
            else:
                out.append('[[%s]]' % target)
        elif target.startswith(('Sokajy:', 'Category:')):
            out.append('[[%s%s]]' % (target, '' if label is None else '|' + label))
        elif target.startswith('#') or '://' in target:
            out.append('[[%s%s]]' % (target, '' if label is None else '|' + label))
        else:
            base = target.split('#')[0]
            if base in verified:
                out.append('[[%s|%s]]' % (verified[base], label if label is not None else verified[base]))
            elif base in mgset:
                out.append('[[%s%s]]' % (target, '' if label is None else '|' + label))
            else:
                out.append(label if label is not None else target)
        last = b
    out.append(s[last:])
    return ''.join(out)


refpat = r'(<ref\b[^>]*/\s*>|<ref\b[^>]*>.*?</ref>)'
t = ''.join(part if re.match(r'<ref\b', part) else transform(part)
            for part in re.split(refpat, t, flags=re.S))

reps = {
    '{{lahatsoratra antsipirihany|Pulmonary surfactant}}': '{{lahatsoratra antsipirihany|Surfactant amin\' ny havokavoka}}',
    '{{lahatsoratra antsipirihany|Respiratory system of the horse}}': '{{lahatsoratra antsipirihany|Rafi-pisefoan\' ny soavaly}}',
    '{{lahatsoratra antsipirihany|Fish physiology#Respiration}}': '{{lahatsoratra antsipirihany|Fiziolôjian\' ny trondro#Fisefoana}}',
    '{{lahatsoratra antsipirihany|Spiracle (arthropods)}}': '{{lahatsoratra antsipirihany|Spirakla (artropôda)}}',
    '{{lahatsoratra antsipirihany|Respiratory system of insects}}': '{{lahatsoratra antsipirihany|Rafi-pisefoan\' ny bibikely}}',
    '{{lahatsoratra antsipirihany|Respiratory system of gastropods}}': '{{lahatsoratra antsipirihany|Rafi-pisefoan\' ny gastrôpôda}}',
    '{{lahatsoratra antsipirihany|Fifohana#Mechanics}}': '{{lahatsoratra antsipirihany|Fifohana#Mekanika}}',
    '{{Page needed|date=September 2010}}': '',
    '{{nbsp}}': ' ',
    '{{ISBN|0-8120-5635-3}}': '<nowiki>ISBN 0-8120-5635-3</nowiki>',
    'na "Hazo fisefoana"{{ordered list |Trakea |Traoka lehibe |Traoka lobara |Traoka segmentara |Bronkiola |Fantsona alveolara |Alveola}}':
        'na "Hazo fisefoana":<br />1) Trakea<br />2) Traoka lehibe<br />3) Traoka lobara<br />4) Traoka segmentara<br />5) Bronkiola<br />6) Fantsona alveolara<br />7) Alveola',
    '[[Sagoaga|filamenta]]': 'filamenta',
    '[[Sagoaga|lamela]]': 'lamela',
    'angsa mpihira, \'\'Cygnus cygnus\'\'': "''whooper swan'' (''Cygnus cygnus'')",
    'faniasy fotsy, \'\'Platalea leucorodia\'\'': "''white spoonbill'' (''Platalea leucorodia'')",
    'gara mikiakiaka, \'\'Grus americana\'\'': "''whooping crane'' (''Grus americana'')",
    'koras\u00f4 misatroka, \'\'Pauxi pauxi\'\'': "''helmeted curassow'' (''Pauxi pauxi'')",
    'androngo monitor': "''monitor lizard''",
    "Haringaron' ny": 'Taolam-body ny',
    "haringaron' ny": 'taolam-body ny',
    'mpanamafy rivotra': 'mpanafofoka rivotra',
}
for a, b in reps.items():
    if a not in t:
        print('MISS', a[:70])
    t = t.replace(a, b)

t = t.replace('\ud83d', '')
# section key line starts with 1) and would trip the Markdown numeric-list lint
t = t.replace('\n1) karandoha', '\n(1) karandoha')
t = t.rstrip('\n')
(JOB / 'draft.wiki').write_bytes(t.encode('utf-8'))
print('bytes', len(t.encode('utf-8')))
