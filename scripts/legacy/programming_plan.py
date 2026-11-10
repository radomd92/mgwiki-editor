"""Offline job plan and immutable term inventory; no network operations."""
import json
import shutil
import subprocess
from pathlib import Path

import mwparserfromhell as mw

from mgwiki_editor.core import write_json

JOB = Path('runs/programming-language-20261109')
PLAN = [
    ('01-lead', 7, 14), ('02-natural-languages', 15, 21),
    ('03-history', 22, 51), ('04-syntax', 52, 98),
    ('05-semantics', 99, 110), ('06-types', 111, 135),
    ('07-concurrency', 136, 139), ('08-exceptions', 140, 148),
    ('09-design', 149, 164), ('10-specification', 165, 174),
    ('11-implementation', 175, 181), ('12-proprietary', 182, 190),
    ('13-use', 191, 243), ('14-dialects', 244, 247),
    ('15-classification', 248, 263), ('16-see-also', 264, 302),
    ('17-references', 303, 305), ('18-reading', 306, 333),
    ('19-end-matter', 334, 346),
]

# English source sense and context-confirmed French bridges, not DB mappings.
TERMS = '''programming language||fiteny fampandaharana|a formal language for expressing computations
formal language|langage formel|fiteny voafaritra amin' ny fitsipika hentitra|a language whose symbols and combinations are precisely specified
computation|calcul|kajy|processing information according to definite rules
source code||kaody loharano|program instructions as written by a programmer
compiler||kaompilatera|software that translates a program before execution
interpreter||mpandika baiko|software that executes a program by interpreting its instructions
machine code||kaody milina|instructions directly executable by a processor
just-in-time compilation||fanangonana kaody ho kaody milina alohan' ny fanatanterahana azy avy hatrany|translation to machine code immediately before execution
bytecode||kaody mpanelanelana|an intermediate instruction representation for a virtual machine
computer architecture||firafitry ny solosaina|the organization of a computer system
imperative programming||fampandaharana mandidy|expressing a computation as an ordered sequence of operations
abstraction||fanafenana ny antsipirian' ny fanatanterahana|exposing essential operations while hiding implementation details
high-level programming language||fiteny fampandaharana avo lenta|a programming language that hides many hardware details
natural language||fiteny voajanahary|a language used by human communities
abstract machine||milina ara-kevitra|a theoretical model of a computing machine
formal specification||famaritana hentitra|a precise description using formally defined notation
Turing-complete||mahatanteraka izay kajy vitan' ny milin' i Turing|able to express any computation performable by a Turing machine
assembly language||fiteny fampikambanana|a symbolic language closely corresponding to machine instructions
portability||fahafahana mamindra amin' ny rafitra hafa|the ability of a program to run on different computer systems
algorithm|algorithme|algôritma|a finite description of steps for solving a problem
arithmetic expression|expression|teny maneho kajy aritmetika|a combination of numerical values and arithmetic operations
mainframe||solosaina vaventy|a large general-purpose computer
floating point|virgule flottante|isa aseho amin' ny faingo mihevaheva|a number represented using a significand and an exponent
functional programming||fampandaharana mifototra amin' ny fampiharana asa|computation expressed by applying functions
recursion|récursivité|fiantsoan' ny asa iray ny tenany|solving a problem by invoking the same procedure on subproblems
conditional expression||teny miankina amin' ny fepetra|an expression whose result depends on a condition
dynamic memory management||fitantanana miovaova ny toerana fitadidiana|allocating and releasing memory during execution
heap||tahirin-toerana fitadidiana azo atokana mandritra ny fanatanterahana|memory used for dynamic allocation
garbage collection||famerenana ho azo ampiasaina ny toerana fitadidiana tsy ilaina intsony|automatic reclamation of memory no longer needed
artificial intelligence||hakingan-tsaina artifisialy|computer techniques for tasks associated with human intelligence
type inference||famantarana ho azy ny karazana angona|determining data types from program context
polymorphism||fahafahana miasa amin' ny karazana angona maro|using a common operation or parameter with different types
parameter|paramètre|masontsivana|a named input specified by a procedure
context-free grammar||fitsipi-panorenana tsy miankina amin' ny manodidina|a formal grammar whose rules replace a single nonterminal independently of its context
object-oriented programming||fampandaharana mifototra amin' ny zavatra|organizing programs around objects combining data and operations
subtype||zana-karazana|a type that specializes another type
dynamic dispatch||fisafidianana ny asa antsoina mandritra ny fanatanterahana|selecting an operation implementation at runtime
inheritance||fandovana toetra|a type or class receiving features from another
pointer||tondro|a value identifying a memory location
logic programming||fampandaharana lôjika|describing facts and rules so that software derives results
formal logic|logique|lôjika voafaritra amin' ny fitsipika hentitra|reasoning governed by explicitly stated formal rules
superset|sur-ensemble|vondrona mahafaoka vondrona hafa|a set containing every element of another set
class||sokajin-javatra|a definition used to create objects with shared structure and behavior
concurrency||fampandehanana baiko mifanindran-dalana|allowing multiple computations to make progress during overlapping time periods
scripting language||fiteny fanoratana baiko ho an' ny mpandika|a language used to run commands through an interpreter
service-oriented programming||fampandaharana mifototra amin' ny tolotra|organizing software as separately running services
distributed computing||kajy zaraina amin' ny solosaina mifandray|computation performed by network-connected components
static typing||famaritana ny karazana angona alohan' ny fanatanterahana|determining expression types before execution
dynamic typing||famaritana ny karazana angona mandritra ny fanatanterahana|associating types with runtime values rather than fixed variable declarations
visual programming language||fiteny fampandaharana an-tsary|a language in which graphical relationships express programs
syntax||fitsipi-panorenana|rules governing the form of valid program text
semantics||hevitra omen' ny fiteny ny kaody|the meaning assigned to valid language constructs
parse tree|arbre|hazo maneho ny firafitry ny kaody|a tree showing a text's grammatical structure
tokenization||fizarana ny kaody ho singa voambolana|breaking text into lexical units
syntax highlighting||fampisongadinana ny singan' ny kaody amin' ny loko|using colors or styles to distinguish syntactic elements
reference implementation||fanatanterahana raisina ho modely|an implementation used as a reference for language behavior
regular expression||lamina mamaritra andian-tsoratra|a formal pattern describing a set of character strings
lexical analysis||famakafakana ny singa voambolana|recognizing the elementary tokens in program text
decimal digit|chiffre|tarehimarika amin' ny fanisana fototra folo|one of the digits 0 through 9
plus sign|plus|marika miampy|the sign indicating addition or a positive number
minus sign|moins|marika manala|the sign indicating subtraction or a negative number
undefined behavior||fihetsika tsy voafaritry ny fiteny|program behavior for which the language imposes no requirements
complex number|complexe|isa voafangaro|a number with a real part and an imaginary part
null pointer||tondro tsy manondro toerana fitadidiana manan-kery|a distinguished pointer value referring to no valid object
type declaration||fanambarana ny karazana angona|an explicit statement of an identifier's data type
variable|variable|ova|a named program entity whose value can change
Chomsky hierarchy||ambaratongan' i Chomsky|a classification of formal grammars by expressive restrictions
undecidable problem||olana tsy ahitana fomba fanapahana ankapobeny|a problem for which no algorithm decides every instance
halting problem||olana momba ny fijanonan' ny fandaharana|deciding whether an arbitrary program eventually stops
macro||baiko mivelatra ho kaody hafa|a construct expanded into other program text
static semantics||fitsipika momba ny hevitry ny kaody azo hamarinina alohan' ny fanatanterahana|semantic restrictions checked without running a program
identifier||anarana famantarana|a name referring to a program entity
case statement||baiko misafidy arakaraka ny sanda|a construct selecting an execution branch by a value
integer|entier|isa feno|a whole number, positive, zero, or negative
function|fonction|asa|a rule or program unit that produces an output from inputs
subroutine||zana-pandaharana|a callable portion of a program
argument||sanda ampitaina amin' ny fiantsoana asa|a value supplied to a procedure or operation
type system||rafitra mamaritra ny karazana angona|rules assigning types and restricting operations on them
data flow analysis||famakafakana ny fivezivezen' ny angona|analysis of how values pass through a program
definite assignment analysis||fanamarinana fa efa nomena sanda ny ova|checking that a variable has been assigned before use
dynamic semantics||fitsipika mamaritra ny fihetsiky ny kaody mandritra ny fanatanterahana|rules defining a program's behavior during execution
control structure||rafitra mifehy ny filaharan' ny baiko|a construct determining which instructions execute and in what order
data type||karazana angona|a set of values and the operations allowed on them
set|ensemble|vondrona|a collection of mathematical objects
value|valeur|sanda|a result or data item denoted by an expression
operation|opération|asa atao|a defined action on one or more values
expression|expression|teny maneho sanda|a combination of symbols evaluated to a value
type equivalence||fitovian' ny karazana angona|the relation determining whether two types count as the same
type compatibility||fifanarahan' ny karazana angona|whether values of one type may be used where another is expected
type theory||teôrian' ny karazana|the formal study of types and typed expressions
bit||bit|a binary information unit
type checking||fanamarinana ny karazana angona|checking that operations use data of permitted types
strong typing||fameperana hentitra ny fifangaroan' ny karazana angona|typing rules that detect invalid combinations unless explicitly converted
weak typing||fameperana malalaka ny fifangaroan' ny karazana angona|typing rules permitting implicit conversions between types
type conversion||fanovana karazana angona|converting a value from one type to another
real number|réel|isa tena izy|a number on the continuous real number line
integer overflow||fihoaran' ny fetra fitahirizana isa feno|an integer result outside the range representable by its type
twos complement||famenon' ny roa|a binary representation of signed integers using the complement relative to a power of two
ones complement||famenon' ny iray|a signed binary representation formed by complementing bits
Boolean||bôleana|having exactly the logical values true and false
byte||okteta|a storage unit conventionally consisting of eight bits
array||tabilao misy singa voalahatra|an indexed collection of data elements
string||andian-tsoratra|a sequence of characters
primitive type||karazana angona fototra|a basic type provided directly by a language
list||lisitra|an ordered collection of elements
associative array||tabilao idirana amin' ny lakile|a collection associating keys with values
record||firaketana|a structured value with named fields
tuple|uplet|andiana sanda voalahatra|an ordered finite grouping of values
enumeration||karazana ahitana sanda voatanisa|a type defined by an explicitly listed collection of possible values
abstract data type||karazana angona afenina ny fomba fanatanterahana azy|a type exposed through operations while hiding its representation
interface||fifandraisana ahazoana mampiasa asa|a defined boundary through which operations are accessed
name collision||fifandonan' ny anarana|distinct program entities using conflicting names
union type||karazana mampiray karazana maro|a type whose values may belong to any of several component types
thread||kofehim-panatanterahana|a sequence of instructions managed as a unit within a process
semaphore||semafôra|a synchronization mechanism controlling access to shared resources
monitor||rafitra manara-maso ny fidirana amin' ny angona iombonana|a synchronization construct coordinating access to shared state
message passing||fifampitana hafatra|communication between computations by sending messages
exception handling||fikarakarana tranga maningana|responding to exceptional conditions during execution
runtime error||hadisoana mandritra ny fanatanterahana|an error arising while a program runs
finalization||fanatanterahana baiko famaranana|running designated cleanup code whether or not an exception occurred
operating system||rafitra fikirakirana|software managing hardware and program execution
assignment||fanomezana sanda|storing a value in a variable
iteration|itération|famerenana|repeating a computation or sequence of instructions
operator overloading||fanomezana hevitra maro ny mpanao asa iray|allowing an operator symbol to denote different operations
orthogonality|orthogonalité|fahaleovantenan' ny singan' ny fiteny|combining language features consistently without many special restrictions
reserved word||teny natokana|a word reserved for a language's syntax rather than user-defined names
expressivity||fahaizana maneho hevitra amin' ny kaody|the range and concision of concepts a language can express
standard library||tahirin' asa mahazatra|a collection of commonly used operations supplied with a language
aliasing||anarana maro manondro toerana fitadidiana iray|different program references accessing the same memory region
specification||famaritana ny fiteny|a document specifying valid programs and their behavior
optimization||fanatsarana ny fampandehanana|transforming code to reduce resource use or improve performance
proprietary language||fiteny fehezin' ny tompony|a language whose implementation or rights are controlled by an owner
domain-specific language||fiteny natokana ho an' ny sehatra iray|a language designed for a particular application domain
open source||misokatra ny kaody loharano|software made available with source code under an open license
pseudocode||kaody fanoritsoritana|an informal algorithm description mixing natural language and code-like notation
primitive||singa fototra|an elementary operation or construct from which programs are built
batch processing||fanodinana anaty andiany|executing grouped work without interactive user input
dialect||endri-piteny|a variant or extension preserving a language's basic nature
data exchange language||fiteny fifanakalozana angona|a notation used to represent and transfer data
S-expression||teny S|a symbolic expression built from atoms and lists
markup language||fiteny fametahana marika|a language annotating content with structural or presentation marks
metaprogramming||fampandaharana mikirakira fandaharana|writing programs that construct or manipulate other programs
reflection||fandinihan' ny fandaharana ny firafiny manokana|a program inspecting or modifying aspects of its own structure
metalanguage||fiteny ilazana fiteny hafa|a language used to describe another language
syntax invariant|invariant|toetra tsy miova|a property maintained throughout specified program operations'''


def main():
    source = (JOB/'source.wiki').read_text(encoding='utf-8')
    lines = source.splitlines(keepends=True)
    plan = []
    for ident, start, end in PLAN:
        directory = JOB/'sections'/ident
        directory.mkdir(parents=True, exist_ok=True)
        (directory/'source.wiki').write_text(''.join(lines[start-1:end]), encoding='utf-8')
        plan.append(dict(id=ident, start=start, end=end, directory=str(directory), status='pending',
                         local_content='Existing article and sandbox absent; no merge content.'))
    write_json(JOB/'section-plan.json', plan)
    inventory = []
    for i, line in enumerate(TERMS.splitlines(), 1):
        en, fr, mg, definition = line.split('|')
        inventory.append(dict(id=f't{i:03}', source_term=en, french_bridge=fr,
                              chosen_expression=mg, english_definition=definition,
                              definition_origin='editorial_simple_english',
                              sections=[p['id'] for p in plan if en.lower() in
                                        (Path(p['directory'])/'source.wiki').read_text().lower()]))
    write_json(JOB/'term-inventory.json', inventory)
    code = mw.parse(source)
    links = [{'target': str(x.title).strip(), 'label': str(x.text or x.title)}
             for x in code.filter_wikilinks()]
    for t in code.filter_templates():
        if str(t.name).strip().lower() in {'main', 'see also', 'details', 'section link'}:
            if t.has('1'):
                links.append({'target': str(t.get('1').value).strip(), 'label': str(t.get('1').value).strip()})
        for p in t.params:
            if 'author-link' in str(p.name) or 'title-link' in str(p.name):
                links.append({'target': str(p.value).strip(), 'label': str(p.value).strip()})
    write_json(JOB/'source-link-inventory.json', links)
    write_json(JOB/'citation-inventory.json', [str(t) for t in code.filter_templates()
                                              if str(t.name).strip().lower().startswith('cite ')])
    refs = {str(t.get('name').value).strip('\"\' '):str(t.contents)
            for t in code.filter_tags() if str(t.tag).lower()=='ref' and t.has('name')
            and not t.self_closing}
    write_json(JOB/'reference-definitions.json', refs)
    shutil.copyfile('data/country-names.json', JOB/'country-names.json')
    e = JOB/'evidence';e.mkdir(exist_ok=True)
    for t in inventory:
        if t['french_bridge']:
            output = e/f"kajy-{t['id']}.json"
            if not output.exists():
                subprocess.run(['python3', '-m', 'mgwiki_editor', 'vocab', '--language', 'fr',
                                '--word', t['french_bridge'], '--output', str(output)],
                               check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['python3', '-m', 'mgwiki_editor', 'vocab-audit', '--draft', str(JOB/'source.wiki'),
                    '--output', str(e/'math-audit-before.json')], check=True, stdout=subprocess.DEVNULL)
    with (JOB/'notes.wiki').open('a', encoding='utf-8') as f:
        f.write('\n## Resume instruction and revised plan\n\n'
                '- User: “please skip that citation and continue”. CITE-001 dangling tag omission authorized; no replacement reference invented. Claim translated faithfully; support gap retained in source-issues.md. Original blocker history above retained.\n'
                '- Generation resumed. Ordered section-plan.json supersedes initial granular outline; coherent History grouped. Each worker owns one listed directory only.\n'
                '- term-inventory.json: English senses, editorial definitions, context-confirmed French bridges, source-section occurrence candidates. SQLite queries in evidence/kajy-t*.json; inspect sense before selecting, not dictionary verification.\n'
                '- source-link-inventory.json and citation-inventory.json retain original link/citation evidence. Country cache pinned as country-names.json.\n')
    write_json(JOB/'status.json', {'status':'in_progress', 'previous_blocker':'CITE-001',
                                  'resolution':'User-authorized omission of undefined reference tag; no replacement invented.',
                                  'save_attempted':False})
    print(len(plan), 'sections;', len(inventory), 'term senses')


if __name__ == '__main__':
    main()
