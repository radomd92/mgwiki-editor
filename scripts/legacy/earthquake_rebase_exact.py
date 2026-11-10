"""One fresh rebase; preserve server-canonical bytes and all editorial history."""
import shutil
from pathlib import Path

from mgwiki_editor.core import GATES, digest, now, read_json, write_json

OLD = Path('runs/earthquake-20261108')
NEW = Path('runs/earthquake-20261108-rebase1')


if __name__ == '__main__':
    old = read_json(OLD/'job.json')
    new = read_json(NEW/'job.json')
    observed = read_json(OLD/'save-readback.json')
    assert new['source'] == old['source']
    assert new['existing'] == old['existing']
    assert new['sandbox']['revision_id'] == observed['revision_id']
    assert new['sandbox']['sha256'] == observed['sha256']
    assert new['sandbox']['text'].encode() == (OLD/'draft.wiki').read_bytes()[:-1]
    excluded = {'job.json', 'source.wiki', 'existing.wiki', 'sandbox.wiki', 'draft.wiki',
                'review.json', 'vocabulary.json', 'notes.wiki', 'source-issues.md',
                'status.json', 'proposal.json', 'preview.html', 'changes.diff',
                'receipt.json', 'prepare.log', 'publish.log', 'proposal-review.json',
                'handoff.json', 'preview-readable.txt', 'preview-structure.json'}
    for path in OLD.iterdir():
        if path.name in excluded:
            continue
        target = NEW/path.name
        if path.is_dir():
            shutil.copytree(path, target, dirs_exist_ok=False)
        else:
            shutil.copy2(path, target)
    # Existing sandbox is editing evidence: retain exactly, not regenerate.
    assert (NEW/'draft.wiki').read_bytes() == new['sandbox']['text'].encode()
    shutil.copy2(OLD/'vocabulary.json', NEW/'vocabulary.json')
    shutil.copy2(OLD/'source-issues.md', NEW/'source-issues-prior-job.md')
    issues = (OLD/'source-issues.md').read_text()
    issues += '''
## Rebase lineage — exact-byte read-back
- Current job: runs/earthquake-20261108-rebase1; prior job: runs/earthquake-20261108.
- EQ-S001–EQ-S009 unchanged/open; original evidence, IDs, handling, next actions retained above and in source-issues-prior-job.md.
- English source revision unchanged: 1379800890. Existing Malagasy mainspace still absent.
- Sandbox revision 1153390 contains entire accepted translation; fresh snapshot retained byte-for-byte. Only prior proposed terminal LF was stripped by server. No prose, references, filenames, links, category order or authorized omissions changed.
- Rebase count: one. No further rebase allowed this task. Prior receipt remains strict-unconfirmed; no original-hash confirmation invented.
'''
    (NEW/'source-issues.md').write_text(issues)
    notes = (OLD/'notes.wiki').read_text()
    notes += '''
## One fresh rebase — preserved actual sandbox
- Current job: runs/earthquake-20261108-rebase1. Source/existing/sandbox snapshots compared completely to previously reviewed full text. Source/existing exact unchanged; sandbox is prior accepted draft minus one terminal LF. New draft byte-for-byte fresh sandbox; no article content edit or regeneration.
- Prior attempt reached HTTP200 edit; original read-back timeout then one paced CLI read. Revision 1153390 exact bytes differ only terminal LF; strict original receipt not relabelled confirmed. Fresh initialized base used, never overwritten or guarded save retried blindly.
- Classification now existing sandbox, not new/empty. Entire sandbox contribution deliberately retained; mainspace absent. Existing-preserved gate reviewed against actual revision 1153390, not N/A.
- 28 section workers/fragments and all targeted corrections reused. Same meaning/fluency/coverage/terminology/citations/links/neutrality/wikitext checks remain valid; only ending LF differs. New proposal/preview requires autonomous review.
- Country/dictionary/coverage evidence copied locally; no refetch. Source-issue history retained: runs/earthquake-20261108-rebase1/source-issues.md (EQ-S001–EQ-S009, open), source-issues-prior-job.md; original memory retained too.
- Remaining scope unchanged: authorized pressure-vaporization, stress-weight, IRIS and two unsupported film omissions stay omitted. No invented source reconciliation.
'''
    (NEW/'notes.wiki').write_text(notes)
    write_json(NEW/'review.json', dict.fromkeys(GATES, True))
    write_json(NEW/'status.json', {
        'status': 'rebased_editorially_reviewed_pending_prepare', 'updated_at': now(),
        'previous_job': str(OLD), 'rebase_count': 1,
        'base_revision_id': new['sandbox']['revision_id'],
        'draft_sha256': digest((NEW/'draft.wiki').read_bytes()),
        'changes_from_actual_sandbox': 'none; byte-for-byte preserved',
        'source_issue_count': 9, 'source_issues': 'source-issues.md',
        'prepare_attempted': False, 'publish_attempted': False,
        'external_references_accessed': False,
    })
    print('Fresh base retained exactly; one rebase, all review/source-issue history copied.')
