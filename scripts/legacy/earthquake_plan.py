"""Offline section plan for the Earthquake translation."""
import shutil
import textwrap
from pathlib import Path

import mwparserfromhell as mw

from mgwiki_editor.core import read_json, write_json

JOB = Path('runs/earthquake-20261108')
PLAN = [
    ('00-lead', 1, 15), ('01-terminology', 16, 22), ('02-examples', 23, 46),
    ('03-faults', 47, 76), ('04-energy', 77, 81), ('05-focus', 82, 89),
    ('06-volcanic', 90, 94), ('07-rupture', 95, 109), ('08-tides', 110, 113),
    ('09-clusters', 114, 128), ('10-frequency', 129, 176), ('11-induced', 177, 180),
    ('12-measurement', 181, 228), ('13-effects', 229, 246), ('14-human', 247, 274),
    ('15-landslides', 275, 279), ('16-fires', 280, 285), ('17-tsunami', 286, 293),
    ('18-floods', 294, 300), ('19-management', 301, 323), ('20-culture', 324, 343),
    ('21-space', 344, 348), ('22-related', 349, 362), ('23-attribution', 363, 371),
    ('24-references', 372, 374), ('25-bibliography', 375, 388),
    ('26-reading', 389, 399), ('27-external', 400, 416),
]


def main():
    source = (JOB/'source.wiki').read_text(encoding='utf-8')
    lines = source.splitlines()
    refs = {}
    plan = []
    for sid, start, end in PLAN:
        directory = JOB/'sections'/sid
        directory.mkdir(parents=True, exist_ok=True)
        raw = '\n'.join(lines[start-1:end])+'\n'
        (directory/'source.wiki').write_text(raw, encoding='utf-8')
        code = mw.parse(raw)
        for tag in list(code.filter_tags()):
            if str(tag.tag).lower() != 'ref':
                continue
            name = str(tag.get('name').value).strip('\"\' ') if tag.has('name') else f'eq-{len(refs)+1:03d}'
            if not tag.self_closing:
                if name in refs and refs[name]['body'] != str(tag.contents):
                    raise RuntimeError('Conflicting reference '+name)
                refs[name] = {'name': name, 'body': str(tag.contents), 'section': sid}
            code.replace(tag, f'<ref name="{name}" />')
        translated = str(code)
        (directory/'translation-source.wiki').write_text(translated, encoding='utf-8')
        (directory/'readable-source.txt').write_text('\n'.join(
            '\n'.join(textwrap.wrap(line, 145, replace_whitespace=False, drop_whitespace=False,
                                   break_long_words=False, break_on_hyphens=False))
            for line in translated.splitlines())+'\n', encoding='utf-8')
        plan.append({'id': sid, 'start': start, 'end': end, 'directory': str(directory),
                     'local_content': 'Both existing article and sandbox absent.',
                     'dependencies': ['shared-context.wiki', 'reference-definitions.json',
                                      'country-names.json'], 'status': 'pending'})
    write_json(JOB/'section-plan.json', plan)
    write_json(JOB/'reference-definitions.json', refs)
    shutil.copyfile('data/country-names.json', JOB/'country-names.json')
    shutil.copyfile('/tmp/opencode/earthquake-title-search.json', JOB/'title-evidence.json')
    (JOB/'shared-context.wiki').write_text("""= Toromarika iombonana =
Source English Earthquake revision 1379800890. Target Horohoron-tany: no existing mainspace or sandbox. Coordinator read all complete snapshots. Local search confirms hyphenated Malagasy term; source has no mg langlink.
Each worker translates ONLY assigned planned section. No network/dictionary/wiki fetching; no nested agents; no shared-file edits. Write only section.wiki, notes.wiki, vocabulary.json in exclusive assigned directory. Load three required skills and local style references in full. Read source.wiki and readable-source.txt completely. translation-source.wiki contains same claims and image/link markup with all refs changed to named reuses; coordinator restores complete definitions centrally. Preserve every ref name and its claim alignment. Do not add reference definitions to fragment.
Full translation, not summary. Preserve numbers, dates, negations, source uncertainty, all images and links including captions. Keep English link targets while translating labels; coordinator maps to verified mg targets or records plain-text fallback. Convert Main/Further/annotated link into native related-text links using original English targets. No guessed local templates. Replace owidslider by its exact embedded File with translated caption; dynamic time slider omitted with reason in notes, static chart retained. Remove maintenance/navigation/authority templates; no live categories/interwiki. Coordinator adds verified inert categories last.
New prose uses amin' ny, an' ny, ho an' ny. Foreign terms italic, full agencies italic with Malagasy explanation, acronym gloss first mention. Names preserve source-supported order; no guessed reversal. Work/paper titles italic, citation metadata protected. Country spellings in country-names.json; missing USA/Canada/Mexico/Peru/Philippines/Tajikistan handled by coordinator with local evidence; temporarily preserve English country labels if uncertain.
Shared DESCRIPTIVE terminology, not claims of established dictionary equivalents:
earthquake = horohoron-tany; seismic wave = onja ateraky ny horohoron-tany; lithosphere = litôsfera (sosona mafy ivelany amin' ny Tany); tectonic plate = takelaka tektônika; fault = vaky misy fifindran' ny vatolampy amin' ny andaniny roa (later: vaky); fault plane = velaran' ny vaky; stress = fihenjanana (force per area), strain = fiovan' endrika (deformation), never conflate; elastic = afaka miverina amin' ny endriny rehefa tsy misy intsony ny hery manova azy; elastic rebound = fiverenan' ny vatolampy amin' ny endriny aorian' ny fitsontsorana tampoka; magnitude = magnitioda (refin' ny haben' ny horohoron-tany any amin' ny niandohany), intensity = hamafin' ny fihovitrovitra tsapa amin' ny toerana iray; hypocenter/focus = foiben' ny fiandohan' ny vaky any anaty tany; epicenter = teboka eo ambonin' ny tany mifanandrify mitsangana amin' ny foibe; normal fault = vaky idinan' ny vato eo ambonin' ny velaran' ny vaky; reverse/thrust fault = vaky iakaran' ny vato eo ambonin' ny velaran' ny vaky; strike-slip fault = vaky ifampisosa mitsivalana ny andaniny roa; subduction = filentehan' ny takelaka iray ao ambanin' ny iray hafa; aftershock = horohoron-tany manaraka ny lehibe; foreshock = horohoron-tany mialoha ny lehibe; swarm = andiana horohoron-tany tsy ahitana iray lehibe miavaka; pore pressure = tsindrin' ny tsiranoka ao amin' ny mason-kelin' ny vatolampy; supershear = fitsotsorana miely haingana noho ny onja S; soil liquefaction = fahaverezan' ny hamafin' ny tany vonton-drano ka itondrany tena toy ny ranoka; tsunami = tsonamy; seismic moment = môman' ny horohoron-tany (vokatry ny fampitomboana ny velaran' ny vaky sy ny halavitry ny fitsotsorana ary ny hamafin' ny vato tsy mety voaova endrika). P/S letters are wave notation, not agency acronyms. P wave longitudinal; S wave transverse.
User requests autonomous save, keeping controversial text rather than deleting it. Preserve attributed disputes and original qualifications, never upgrade conjecture to fact. Frequency source has decreased/increased statements from different dated references: present with dates/attribution, not manufactured consistent trend. Tangshan lead over 300,000 vs body range 240,000–655,000: use body range in lead and note editorial reconciliation. Do not suppress controversy. Material unresolved high-risk meaning/citation/copyright/merge problems must still be reported to coordinator, not hidden.
Source wording has technical simplifications: depth of epicenter should be depth of focus (epicenter surface by definition). Moment magnitude relates to seismic moment, not identical to directly measured radiated energy: preserve distinction already explained in source. Do not invent corrective facts; report any issue.
Vocabulary JSON: list of records with source_term, source_language=en, domain, source_sense, english_definition (simple English), definition_origin=editorial_simple_english, malagasy_definition, chosen_expression, evidence_files (local source.wiki relative to your directory), alternatives_rejected, status=descriptive or unresolved, reason. Report missing dictionary needs. Coordinator does lookups later, not worker. Ordinary descriptive precision is acceptable; never claim unverified labels established.
Article-level gates and publication are coordinator-only. Your fragment is not final editorial approval.
""", encoding='utf-8')
    state = read_json(JOB/'job.json')
    with (JOB/'notes.wiki').open('a', encoding='utf-8') as notes:
        notes.write('\n== Fandraisana sy fiaviana ==\nLahatsoratra vaovao; mainspace sy sandbox samy tsy misy. Loharano: '+state['source']['url']+'. Dika avy amin’ ny Wikipedia anglisy, CC BY-SA; tsy nosokafana ny citation URLs. Tsy misy fandraisana anjara malagasy ho very. Mpampiasa nangataka hitazona adihevitra miaraka amin’ ny qualification, tsy hanafoana vavahady fiarovana.\n== Drafitra voalamina ==\n')
        for item in plan:
            notes.write(f"* {item['id']}: source {item['start']}–{item['end']}; {item['directory']}; pending; local absent; dependencies shared-context, references, country evidence.\n")
    write_json(JOB/'status.json', {'status': 'translating', 'retain_attributed_controversy': True})


if __name__ == '__main__':
    main()
