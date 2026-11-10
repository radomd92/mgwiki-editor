"""Targeted coordinator style repairs after accepted-fragment integration."""
import textwrap

import mwparserfromhell as mw

from mgwiki_editor.core import write_json
from programming_plan import JOB

TITLES = [
    'The Prentice-Hall standard glossary of computer terminology',
    'Programming Languages and Computers: A Unified Metatheory',
    'Advances in computers',
    'Some thoughts on teaching programming and programming languages',
    'Visual programming languages integrated across the curriculum in elementary school: A two year case study using "Scratch" in five schools',
    'Beginning Ballerina Programming: From Novice to Professional',
    'Artificial intelligence based smart door with face mask detection',
    'Blueprints visual scripting for unreal engine',
    'Hands-On Game Development without Coding: Create 2D and 3D games with Visual Scripting in Unity',
    'Perl and Undecidability', 'Lecture Notes: Macros',
    'On the foolishness of "natural language programming."',
    'Finding code on the World Wide Web: a preliminary investigation',
    'Programming Language Rexx',
]


if __name__=='__main__':
    p=JOB/'draft.wiki';text=p.read_text(encoding='utf-8');changes=[]
    substitutions={
        '<span id="English-like programming languages"></span>':'<span id="English-like_programming_languages"></span>',
        'Eo amin\' ny sehatry ny informatika,':'Eo amin\' ny sehatry ny kajimirindra,',
        'solosaina foibe lehibe':'solosaina vaventy',
        "Jereo ny lahatsoratra momba ny tantaran' ny fiteny fampandaharana.":"Lohahevitra mifandray: tantaran' ny fiteny fampandaharana.",
        "Ny lahatsoratra Fitsipi-panorenan' ny fiteny fampandaharana no miresaka manokana io lohahevitra io.":"Lohahevitra mifandray: fitsipi-panorenan' ny fiteny fampandaharana.",
        "Ny lahatsoratra Hevitra omen' ny fiteny fampandaharana ny kaody no mamelabelatra izany.":"Lohahevitra mifandray: hevitra omen' ny fiteny fampandaharana ny kaody.",
        'Lahatsoratra momba ity lohahevitra ity: Fikarakarana tranga maningana.':'Lohahevitra mifandray: fikarakarana tranga maningana.',
        'Lahatsoratra fototra: Famolavolana sy fanatanterahana ny fiteny fampandaharana.':'Lohahevitra mifandray: famolavolana sy fanatanterahana ny fiteny fampandaharana.',
        'Lahatsoratra fototra: Fampiharana fiteny fampandaharana.':'Lohahevitra mifandray: fampiharana fiteny fampandaharana.',
        "Jereo koa ny vakiteny fanampiny momba ny tantaran' ny fiteny fampandaharana.":"Lohahevitra mifandray: vakiteny fanampiny momba ny tantaran' ny fiteny fampandaharana.",
    }
    for old,new in substitutions.items():
        if old in text:
            text=text.replace(old,new)
            changes.append({'old':old,'new':new,'reason':'targeted style/terminology or unavailable-link navigation fallback'})
    code=mw.parse(text)
    for t in code.filter_tags():
        if str(t.tag).lower()!='ref' or t.self_closing:
            continue
        body=str(t.contents)
        oldbody=body
        if body.startswith('See: Oracle America'):
            body='Jereo: '+body[len('See: '):]
        if 'title-link: Introduction to the Theory of Computation. ' in body:
            body=body.replace('title-link: Introduction to the Theory of Computation. ','')
        for title in TITLES:
            if title in body and "''"+title+"''" not in body:
                body=body.replace(title,"''"+title+"''",1)
        if body.startswith('Kodosky, J., 2020. LabVIEW.'):
            body=body.replace('2020. LabVIEW.','2020. \'\'LabVIEW\'\'.',1)
        if body!=oldbody:
            t.contents=body
            changes.append({'kind':'reference_display_style',
                            'reason':'original titles italicized; original names/wording/URLs/IDs/quotes retained; See translated; duplicate title-link directive omitted'})
    text=str(code)
    p.write_text(text,encoding='utf-8')
    write_json(JOB/'coordinator-refinements.json',changes)
    (JOB/'draft-readable.txt').write_text('\n'.join('\n'.join(textwrap.wrap(
         line,140,replace_whitespace=False,drop_whitespace=False,break_long_words=False,
         break_on_hyphens=False)) for line in text.splitlines())+'\n',encoding='utf-8')
    print(len(changes),'targeted display/wording repairs; no source prose regenerated')
