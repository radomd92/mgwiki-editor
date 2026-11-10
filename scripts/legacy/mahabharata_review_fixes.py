"""Narrow coordinator corrections after full assembled-wikitext review."""
from pathlib import Path
import shutil
import re
import textwrap

JOB=Path('runs/mahabharata-20261108')


if __name__=='__main__':
    p=JOB/'draft.wiki'; text=p.read_text(encoding='utf-8')
    replacements={
        "dia iray amin' ireo tononkalo mitantara ny asan' ny mahery fo roa lehibe amin' ny literatiora sanskrita":
        "dia iray amin' ireo tononkalo roa lehibe mitantara ny asan' ny mahery fo amin' ny literatiora sanskrita",
        "Adhisimakrishna (zana-dohalik' i Parikshit)":"Adhisimakrishna (zafiafin' i Parikshit)",
        "ny zava-bitany be voninahitra":"ny zava-bitany",
        "Yudhishthira be voninahitra":"Yudhishthira",
        "lalao ampiasana ''dice'' (zavatra kely misy marika atsipy mba hahazoana vokatra kisendrasendra)":
        "lalao fanipazana goba (zavatra kely misy marika atsipy mba hahazoana vokatra kisendrasendra)",
        "ny hany fanontana, amin' izay fiteny misy azy,":"ny hany fanontana amin' ireo fiteny rehetra ",
        "havoaka no efa misy araka ny loharano.":"havoaka no efa misy.",
        "amin' ny fanontana Munshiram Manoharlal ampiasain' ny loharano.":"amin' ny fanontana Munshiram Manoharlal.",
        "Ny tantara an-tsehatra manan-danja voalohany tamin' ny taonjato faha-20 dia ny":
        "Anisan' ireo tantara an-tsehatra tamin' ny taonjato faha-20 nipoitra avy amin' ny ''Mahābhārata'' ny",
        "Ny filaharan' ny iray tam-po eo amin' ny tetiarana niandohana, avy ankavia miankavanana, dia":
        "Ny filaharan' ny iray tam-po ao amin' ity tetiarana ity dia",
        '[[Fiteny tamily|teny tamila]]':'[[Fiteny tamily|teny tamily]]',
        '[[Fiteny kanada|kannada]]':'[[Fiteny kanada|kanada]]',
        'teny kannada':'teny kanada',
        '[[Fiteny malaialama|malayalam]]':'[[Fiteny malaialama|malaialama]]',
        '[[Fiteny ôdià|teny odia]]':'[[Fiteny ôdià|teny ôdià]]',
        '[[Fiteny hindỳ|hindy]]':'[[Fiteny hindỳ|hindỳ]]',
        'teny hindy':'teny hindỳ',
        '[[Fiteny hindỳ|teny hindi]]':'[[Fiteny hindỳ|teny hindỳ]]',
        '[[Empira Môgôly|Empira Mughal]]':'[[Empira Môgôly]]',
        'chapter-url: https://archive.org/details/mahabharata0000raja.':
        "[https://archive.org/details/mahabharata0000raja rohy mankany amin' ny toko].",
        "Mazava ho azy fa ''kāvya'' izy, ary ''shastra'' koa":
        "Mazava ho azy fa tononkalo (''kāvya'') izy, ary soratra fampianarana (''shastra'') koa",
        'nahitana tanimanga volondavenona misy hosodoko':
        "nahitana zavatra vita amin' ny tanimanga volondavenona misy hosodoko",
        'rehetra  mampiditra':'rehetra mampiditra',
        "ny fampifanarahana ho an' ny teatra nokasain' i [[Satyajit Ray]]":
        "ny fampifanarahana nokasain' i [[Satyajit Ray]]",
        "ny Amar Chitra Katha.<ref":
        "ny ''Amar Chitra Katha'' (orinasa mpamoaka boky).<ref",
        'fivahinianana masina':'fivahiniana masina',
        "izay soloin' i Vrddha Garga, Varāhamihira ary Kalhana tena,":
        "izay ahitana an' i Vrddha Garga sy Varāhamihira ary Kalhana,",
    }
    applied=[]
    for old,new in replacements.items():
        n=text.count(old)
        if n: text=text.replace(old,new); applied.append((old,new,n))
    color="Ao amin' ny tetiarana niandohana, ny sisiny manga dia manondro lehilahy, ary ny sisiny mena kosa manondro vehivavy. Ny boaty maitso dia manondro ny Pandava, ary ny boaty mavo manondro ny Kaurava. Soratana mivantana amin' ny teny ireo fanavahana ireo eto fa tsy aseho amin' ny loko fotsiny."
    if color in text:
        text=text.replace(color+'\n','')
        applied.append(('Decorative original-tree color-key commentary','Male/female and Pandava/Kaurava labels already explicit in native tables',1))
    text=re.sub(r'\n{3,}','\n\n',text)
    p.write_text(text,encoding='utf-8')
    shutil.copyfile('runs/united-states-dollar-20261104/metadata-local-country-exceptions.json',JOB/'evidence/reused-country-exceptions.json')
    with (JOB/'notes.wiki').open('a',encoding='utf-8') as f:
        f.write('\n== Fanitsiana nataon’ ny coordinator taorian’ ny famakiana ny draft feno ==\n')
        for old,new,n in applied: f.write(f'* {old} → {new} ({n}).\n')
        f.write('''Ny teny filaharana zafiafy no mitovy amin' ny great-grandson; tsy natao ho taranaka hafa ny Adhisimakrishna. Ny isa sy filaharana rehetra hafa dia nijanona. Nesorina ny fiderana tsy voafaritra (glorious) sy ranking teatra tsy misy sehatra mazava, fa ny asa sy ny taona sy ny citations rehetra nijanona. Ny fanazavana loko eo amin' ny tetiarana niandohana dia presentation-only, tsy votoaty ara-pihavanana; ny lahy/vavy sy Pandava/Kaurava efa voalaza mivantana amin' ny tabilao vaovao.
Ny Singaporo dia tsy ao amin' ny cache firenena fa voamarina amin' ny porofo mg teo aloha (pejy 8938, revision 1149935, title Singaporo) voatahiry eto. Ilay firenena sady tanàna marina no asehon' ny extract. Scotland dia anaran-toerana nalaina tamin' ny source caption, tsy atao porofon' ny fiandrianam-pirenena na soloina teny malagasy novinavinaina. Bangladesh ao amin' ny bibliografia dia metadata original ka tsy novaina.
Ny approximate date 1900 ao amin' ny caption Draupadi and Pandavas dia voatahiry araka ny source; approximate 1910 kosa ny metadata DateTimeOriginal. Tsy natao daty marina tsy misy ahiahy ny iray amin' izy roa; tsy nisokatra ny sary na external URL. Tsy misy olana copyright: shared Commons Public domain ny rakitra.
''')
    (JOB/'draft-readable.txt').write_text('\n'.join('\n'.join(textwrap.wrap(l,170,break_long_words=False,break_on_hyphens=False,replace_whitespace=False,drop_whitespace=False)) for l in text.splitlines()),encoding='utf-8')
    print('Applied',len(applied),'narrow editorial corrections.')
