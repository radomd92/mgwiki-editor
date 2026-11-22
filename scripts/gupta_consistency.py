"""Apply explicitly reviewed proper-name variants; protect source reference data."""
import re
from pathlib import Path
import mwparserfromhell as mw

p=Path('runs/gupta-empire-20261122')
f=p/'draft.wiki'
s=f.read_text(encoding='utf-8')
for ref in mw.parse(s).filter_tags():
    if str(ref.tag)=='ref' and ref.contents is not None:
        assert not re.search(r'\b(?:Hona|Hôna|Kidarita)\b',str(ref.contents))
# Every occurrence inventoried/reviewed: infobox, lead, decline, military only.
s=re.sub(r'\b(?:Hona|Hôna)\b','Huna',s)
s=re.sub(r'\bKidarita\b','Kidarites',s)
s=s.replace('{{sfn|Rowland|1967|pp=219–220}}','<ref>Rowland (1967), pp. 219–220</ref>')
s=s.replace('{{sfn|Michell|1988|p=94}}','<ref>Michell (1988), p. 94</ref>')
s=s.replace('« Huns Fotsy »','« Huna Fotsy »')
s=s.replace('«Mpanjaka lehibe, Andriamatoa Gupta»','«Mpanjaka lehibe, Tompo Gupta»')
f.write_text(s,encoding='utf-8')
