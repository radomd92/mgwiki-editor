"""Persist nonblocking source concerns and exact pinned evidence; no remote operations."""
from pathlib import Path

from mgwiki_editor.core import now, read_json

JOB = Path('runs/earthquake-20261108')


def main():
    prior = JOB/'source-issues.md'
    history = JOB/'source-issues-before-20261109.md'
    if prior.exists() and not history.exists():
        history.write_bytes(prior.read_bytes())
    state = read_json(JOB/'job.json')
    source = (JOB/'source.wiki').read_text(encoding='utf-8').splitlines()
    refs = read_json(JOB/'reference-definitions.json')
    issues = [
        ('EQ-S001', 'Frequency reports, different dates', [135, 144, 153], ['eq-043', 'eq-044', 'eq-046'],
         'USGS average stable/decrease versus Australian Geographic increase. Different dates; no validated common time series.',
         'Both dated attributed reports retained. No winner, merged trend, or new research.',
         'Compare original statistical periods if later external research authorized.'),
        ('EQ-S002', 'Pressure and vaporization causal wording', [107, 108], ['Sibson', 'Rudnicki'],
         'Source says pressure rise consequently increases vaporization. Worker questions causal wording; no opposing external source was opened.',
         'Initial draft translated sentence; user subsequently authorized omission. Sentence and its now-unused two references omitted; later Nur discussion retained. Omission is not factual resolution.',
         'Check original thermal-fluid argument if passage is ever restored.'),
        ('EQ-S003', 'Stress compared with weight', [75], ['eq-015'],
         'Source equates principal stress with force/weight. Lexical stress sense is force per area; equality needs dimensional context. No external reference read.',
         'Initial descriptive repair attempted; later user-authorized omission removes simplified explanation only. Hierarchy and stress-drop conclusion retained. Prior unresolved interpretation remains archived in omitted-vocabulary.json, not active lexical blockers.',
         'Verify dimensional assumptions against original mechanics reference before any restoration.'),
        ('EQ-S004', 'Magnitude, energy and direct proportionality', [78, 80, 189], ['eq-016', 'eq-017', 'eq-059'],
         'Source gives multiplicative energy per magnitude unit, then joins energy and magnitude under direct proportionality to area/stress drop.',
         'Magnitude dependence separated from energy proportionality; no new quantitative law added. Bomb comparison attributed to named 2018 item; no unspecified yield invented.',
         'Review original fault-scaling argument and bomb-comparison assumptions. Wording change not scientific adjudication.'),
        ('EQ-S005', 'Tangshan death-count summaries', [12, 29], ['eq-003'],
         'Lead over 300,000 versus body range 240,000–655,000. Range overlaps threshold; source still presents different certainty.',
         'Draft lead repeats cited body range, preserving uncertainty rather than selecting a point estimate. Original threshold retained here.',
         'Compare casualty definitions and estimates if later source research authorized.'),
        ('EQ-S006', 'Moment magnitude versus energy wording', [184, 191], ['eq-060', 'eq-061'],
         'Source first defines moment-based scale using area/slip/rigidity, later identifies actual released energy with static seismic moment.',
         'Retain explicit moment-based definition. Omit energy-identification phrasing and unneeded added radiated-energy contrast; no new reconciliation claimed.',
         'Review moment/energy wording against Bormann and Di Giacomo before expanding explanation.'),
        ('EQ-S007', 'Fiction genres and citation chronology', [340, 342], ['Van Riper 60'],
         'Source labels list novels while including 2012 (2009) and San Andreas (2015); attached Van Riper reference is dated 2002.',
         'Worker ID 20-culture-CITE-01 retained as alias. Initial genre neutralization to works retained. Later targeted 20-culture-final drops two post-2002 film examples under user authorization; two earlier novels and citation remain. Original list/metadata retained here.',
         'Supply a suitable later citation before restoring film examples; do not infer support from 2002 reference.'),
        ('EQ-S008', 'Local Haiti title date differs from its own extract', [235], [],
         'English target 2010 Haiti earthquake maps to Malagasy title containing 26 Janoary 2010, while local extract says 12 Janoary 2010.',
         'Same event confirmed from local extract (Port-au-Prince, magnitude, date); exact existing local link title retained. Caption says January 2010, not the erroneous title date. No mainspace move/edit.',
         'Later local title/content review by authorized editor; keep existing target until verified title change.'),
        ('EQ-S009', 'Thales dates differ in auxiliary local identity extract', [334], ['World'],
         'Pinned English account gives 625–547 BCE; auxiliary Malagasy Thales extract gives birth -623 and death -546. Local extract used for identity, not as replacement date authority.',
         'English account/dates and its World citation retained; existing local Thales link retained. No merged date, invented reconciliation, or biography edit.',
         'Compare historical date estimates if later research authorized; retain both evidence paths.'),
    ]
    out = [
        '# Source issues', '',
        f'Article/job: Earthquake → Horohoron-tany; `{JOB}`.',
        f'Pinned source: revision {state["source"]["revision_id"]}; `source.wiki`; {state["source"]["url"]}.',
        'Status: nine open review issues. Open alone never blocks sandbox publication. Independent meaning/citation/save guards remain.',
        'History: initial keep-all request; later user authorized problematic-passage omissions; latest request continues that scope. No omitted passage restored merely because policy changed.',
        'External citations: metadata preserved only; not opened. Dictionaries: lexical evidence only, not article-fact sources.',
        'Prior consolidation retained in `source-issues-before-20261109.md`; existing IDs/evidence/history carried forward.',
        f'Consolidated: {now()}. Source text/quotes below exact pinned evidence.', '',
    ]
    for iid, heading, numbers, citations, conflict, handling, action in issues:
        out += [f'## {iid} — {heading}', '- Status: open.',
                f'- Article/job: Earthquake → Horohoron-tany; `{JOB}`.',
                f'- Pinned source: revision {state["source"]["revision_id"]}; `source.wiki`; lines '+', '.join(map(str, numbers))+'.',
                '- Conflict/review concern: '+conflict,
                '- Draft handling/history: '+handling, '- Next review: '+action,
                '- Exact pinned source:']
        for n in numbers:
            out += [f'  - Line {n}:', '', '> '+source[n-1], '']
        if citations:
            out.append('- Pinned citation metadata:')
            for name in citations:
                out += ['  - `'+name+'`:', '', '> '+refs[name]['body'].replace('\n', '\n> '), '']
        if iid == 'EQ-S008':
            data = read_json(JOB/'evidence/local-000.json')['response']['query']['pages']
            local = next(p for p in data if p['title'].startswith('Horohorontany any Haiti'))
            out += [f'- Local evidence: `evidence/local-000.json`; revision {local["lastrevid"]}; title exact:',
                    '', '> '+local['title'], '', '- Local extract exact:', '', '> '+local['extract'], '']
        if iid == 'EQ-S009':
            pages = read_json(JOB/'evidence/local-identity.json')['response']['query']['pages']
            local = next(p for p in pages if p['title'] == 'Thales')
            out += ['- Auxiliary local identity evidence: `evidence/local-identity.json`, pageid 190237; revision 1111731 pinned separately in `evidence/local-000.json`.',
                    '', '> '+local['extract'], '']
    (JOB/'source-issues.md').write_text('\n'.join(out)+'\n', encoding='utf-8')
    with (JOB/'notes.wiki').open('a', encoding='utf-8') as f:
        f.write('\n## Source-issue memory\n`runs/earthquake-20261108/source-issues.md`: EQ-S001–EQ-S009, open. Source disagreements nonblocking; user-authorized omissions remain. Prior notes/history retained, not erased. No external references opened.\n')
    print('Nine durable source issues recorded; nonblocking, history preserved.')


if __name__ == '__main__':
    main()
