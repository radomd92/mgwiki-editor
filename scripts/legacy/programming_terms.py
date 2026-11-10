"""Coordinator's sense selections and supplemental offline mathematical queries."""
import subprocess

from programming_plan import JOB
from mgwiki_editor.core import read_json, write_json


if __name__=='__main__':
    terms=read_json(JOB/'term-inventory.json')
    by={t['source_term']:t for t in terms}
    for term,bridge in {
        'context-free grammar':'grammaire non contextuelle',
        'Turing-complete':'Turing-complet', 'regular expression':'expression régulière',
        'undecidable problem':'indécidable', 'halting problem':"problème de l’arrêt",
        'type theory':'théorie des types', 'conditional expression':'expression conditionnelle',
    }.items():
        by[term]['french_bridge']=bridge
    for term,mg,number,reason in [
        ('integer','isa tsimivaky',454,'Select Entier (nombre), not Entière (série); integer = whole number. Isa feno remains existing local label, not chosen article terminology.'),
        ('complex number','isa haro',163,'Complex-valued arithmetic context; introduce explanatory wording, not ordinary complicated.'),
        ('real number','isa voatsapa',499,'Select mathematical Réel; retain English gloss and explain when needed, not everyday real.'),
        ('function','lefa',215,'Select mathematical/input-output function; not dominated/trigonometric/elementary qualifiers. Programming subroutine remains zana-pandaharana.'),
        ('set','vondrona',485,'Select unqualified Ensemble; not interior/diameter/product.'),
        ('value','sanda',398,'Select unqualified Valeur; not spectral value.'),
    ]:
        by[term].update(chosen_expression=mg,selected_source_numbers=[number],selection_reason=reason)
    by['functional programming']['chosen_expression']="fampandaharana mifototra amin' ny lefa"
    extra='''number|nombre|isa|a mathematical quantity or numeral
positive integer|entier positif|isa tsimivaky miabo|an integer greater than zero
negative number|négatif|isa miiba|a number less than zero
addition|addition|fanampiana|combining numerical quantities by adding
subtraction|soustraction|fanalana|finding the difference of numerical quantities
precision|précision|fahamarinan' ny fanehoana isa|the detail with which a numerical value is represented
theorem|théorème|teôrema|a mathematical statement proved from assumptions
Backus–Naur form|forme de Backus-Naur|endrika Backus–Naur|a notation for specifying a formal grammar
type-2 grammar|grammaire de type 2|fitsipi-panorenana karazany 2|a context-free grammar in the Chomsky hierarchy
binary|binaire|mifototra amin' ny roa|using two possible digit values
symbol|symbole|marika|a sign used to represent an entity or operation'''
    for line in extra.splitlines():
        en,fr,mg,definition=line.split('|')
        if en not in by:
            item=dict(id=f't{len(terms)+1:03}',source_term=en,french_bridge=fr,
                      chosen_expression=mg,english_definition=definition,
                      definition_origin='editorial_simple_english',sections=[])
            terms.append(item);by[en]=item
    for t in terms:
        if t['french_bridge']:
            output=JOB/'evidence'/f"kajy-{t['id']}.json"
            if not output.exists():
                subprocess.run(['python3','-m','mgwiki_editor','vocab','--language','fr',
                                '--word',t['french_bridge'],'--output',str(output)],
                               check=True,stdout=subprocess.DEVNULL)
    write_json(JOB/'term-inventory.json',terms)
    print(len(terms),'term senses; inspect supplemental query results before workers')
