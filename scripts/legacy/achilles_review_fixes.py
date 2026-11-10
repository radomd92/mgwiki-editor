"""Small final changes discovered during assembled raw-wikitext review."""
from pathlib import Path
import re
from mgwiki_editor.core import write_json, lint_wikitext

J=Path('runs/achilles-20261107')


def main():
    text=(J/'draft.wiki').read_text(encoding='utf-8')
    saved=[]
    pattern=r'<ref\b[^>]*/\s*>|<ref\b[^>]*>.*?</ref>|<nowiki\b[^>]*>.*?</nowiki>|\[\[(?:File|Image):[^|\]]+|https?://[^\s\]<>|]+|\'\'[^\n]*?\'\''
    def protect(m):saved.append(m[0]);return f'\x00P{len(saved)-1}\x00'
    body=re.sub(pattern,protect,text,flags=re.S|re.I)
    body=re.sub(r'\bTroy\b','Trôia',body)
    body=body.replace('maty tsy tonga taona',"maty talohan' ny fotoana")
    body=body.replace('ny Achaeans','ny Grika').replace('tafika akeana','tafika grika')
    for i,value in enumerate(saved):body=body.replace(f'\x00P{i}\x00',value)
    text=body
    text=text.replace("''Iliad'' ao anatiny","''Iliada'' ao anatiny").replace("''Iliad'' ilay tantara","''Iliada'' ilay tantara")
    text=text.replace("''Iliada'' nosoratan' i [[Hômerôsy|Homer]]", "''Iliada'' (''Iliad'' amin' ny teny anglisy) nosoratan' i [[Hômerôsy|Homer]]",1)
    old="Nisy sambo mpiady mifono vy karazana ''cruiser'', izany hoe sambo mpiady antonony habe afaka mandeha lavitra nitondra io anarana io koa niasa tao amin' ny ''Royal Navy'' nandritra ny Ady Lehibe Voalohany."
    new="Nisy sambo mpiady mifono vy nitondra io anarana io koa niasa tao amin' ny ''Royal Navy'' nandritra ny Ady Lehibe Voalohany. Karazana ''cruiser'' izy io, izany hoe sambo mpiady antonony habe afaka mandeha lavitra."
    assert old in text
    text=text.replace(old,new)
    text=text.replace("ilay mpanoratra fantatra amin' ny anarana hoe ''First Vatican Mythographer''", "ilay mpanoratra fantatra amin' ny anarana hoe ''First Vatican Mythographer'' (mpanangona angano voalohany ao amin' ny Vatikana)")
    (J/'draft.wiki').write_text(text,encoding='utf-8')
    with (J/'notes.wiki').open('a',encoding='utf-8') as f:
        f.write("\nNy famakiana ny drafitra tafatambatra dia nanitsy ny fehezanteny cruiser mba ho fehezanteny roa mazava, nampiditra gloss ho an' ny anarana fanondroana First Vatican Mythographer, ary nampifanaraka ny fanononana ny Iliada tao amin' ny literatiora maoderina. Iliad no lohateny anglisy hita amin' ny fanononana; ny fampidirana dia milaza an' io endrika io mazava, ary tsy milaza fa misy fanontana na pejy mg voamarina mitondra ny lohateny Iliada. Nohamarinin' ny mpandrindra ny fanavahana ny self-closing ref sy ny ref misy famaritana mba tsy hahafeno amin' ny fahadisoana ireo elanelan-teny tokony hojerena. Tsy misy citation/URL/filename novana tamin' io fanitsiana io.\n")
    write_json(J/'final-lint.json',dict(errors=lint_wikitext(text)))


if __name__=='__main__':main()
