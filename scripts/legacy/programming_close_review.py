"""Close evidenced terminology review before guarded preparation; no network/save."""
from mgwiki_editor.core import digest, now, read_json, write_json
from programming_plan import JOB


if __name__ == '__main__':
    reconciliation = read_json(JOB / 'terminology-reconciliation.json')
    records = read_json(JOB / 'vocabulary.json')
    if reconciliation['unmatched_terms'] or any(
        not r.get('research_complete') or r.get('pending_evidence_files')
        or r['status'] == 'unresolved' for r in records
    ):
        raise RuntimeError('Unfinished terminology evidence; gates unchanged.')
    extra = {
        'all-reviewed-terms.json', 'all-reviewed-terms.txt',
        'terminology-reconciliation.json', 'dictionary-final-review.json',
        'source-issue-index.json', 'coverage-audit.json',
    }
    records[0]['evidence_files'] = sorted(set(records[0]['evidence_files']) | extra)
    for r in records:
        for name in r['evidence_files']:
            if not (JOB / name).is_file():
                raise RuntimeError('Missing evidence: ' + name)
    write_json(JOB / 'vocabulary.json', records)
    unknown = JOB / 'unknown-vocabulary.wiki'
    with unknown.open('a', encoding='utf-8') as f:
        f.write('\n## Final coordinator disposition\n\n'
                '- Historical item-level next actions above retained, superseded here: '
                'dictionary/sense review complete. No unresolved material meanings. '
                '254 sense records reconciled; 277-entry review inventory includes aliases, '
                'names and ordinary labels, not 277 unresolved terms.\n'
                '- Accurate descriptive Malagasy retained where one-word attestation weak. '
                'No failed lookup relabelled verified. Preferred-label refinement remains '
                'optional later research, not deferred meaning.\n'
                '- Decisions/evidence: dictionary-final-review.md, '
                'dictionary-final-review.json, terminology-reconciliation.json, vocabulary.json. '
                'Source disagreements separate: source-issues.md, 17 open.\n')
    sha = digest((JOB / 'draft.wiki').read_bytes())
    with (JOB / 'notes.wiki').open('a', encoding='utf-8') as f:
        f.write('\n## Final raw editorial review\n\n'
                '- Earlier deferred status historical; user-requested retry recovered. '
                'Base156/supplement141 planned outputs complete; cache reuse and canonical '
                'headword follow-ups preserved. No bypass or concurrent wiki worker.\n'
                '- Complete source and latest raw draft reread; empty existing/sandbox '
                'snapshots reconfirmed locally. Final process correction distinguishes '
                'separate running-program instance from phase/thread. Source code, numbers, '
                'qualifications, five Commons filenames and citation/URL coverage retained.\n'
                '- Terminology reconciled: 254 records, no unmatched research/pending files '
                'or unresolved material meanings. Simple English/Malagasy definitions reviewed; '
                'weak/noisy dictionary senses rejected. Descriptive wording not presented '
                'as established compound terminology. dictionary-final-review.md/json; '
                'terminology-reconciliation.json. 277-entry inventory supplied to user; '
                'unknown-vocabulary.wiki final disposition supersedes historical pending actions.\n'
                '- Math SQLite sense/bridge evidence retained; final partial audit two '
                'protected matches only. Manual English/headings/captions/list-label review '
                'complete. Apostrophe spacing, acronym glosses, foreign/title italics, '
                'original name order and protected citation strings checked again. '
                'Country/local topic evidence pinned; plain-text unmapped topics documented.\n'
                '- Citation exception limited to user-authorized undefined :59 tag. '
                'No reference invented or external citation accessed. Source issues: '
                'source-issues.md, 17 open; retained independently from review gates. '
                'No copyright, sensitive-content, citation-integrity or identity blocker found.\n'
                '- Validation clean; python3 -m pytest: 271 passed; '
                'ruff check mgwiki_editor tests: passed. No commit/push; unrelated changes untouched.\n'
                '- Destination: Mpikambana:Bot-Jagwar/Fiteny fampandaharana. Attribution: '
                'https://en.wikipedia.org/w/index.php?oldid=1384004129. '
                'Prepare will produce changes.diff/proposal.json/preview.html; '
                'offline rendered review still required, then exact guarded save/read-back. '
                'No human approval claimed.\n'
                '- Final raw draft SHA256: ' + sha + '.\n')
    review = read_json(JOB / 'review.json')
    review['terminology'] = True
    write_json(JOB / 'review.json', review)
    state = read_json(JOB / 'status.json')
    state.update(status='raw_review_complete', recorded_at=now(), draft_sha256=sha,
                 reason='Dictionary retry recovered; terminology reconciled, raw editorial gates complete.',
                 pending=['guarded prepare/live revisions', 'offline rendered review',
                          'sandbox publish/read-back'], prepare_attempted=False, save_attempted=False)
    write_json(JOB / 'status.json', state)
    print('Raw review complete; rendered review pending. Draft SHA256:', sha)
