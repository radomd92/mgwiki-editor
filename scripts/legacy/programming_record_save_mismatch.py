"""Record one inspected mismatch locally; never save or relax exact-byte guards."""
from pathlib import Path

from mgwiki_editor.core import digest, now, read_json, write_json

JOB = Path('runs/programming-language-20261109')


if __name__ == '__main__':
    receipt = read_json(JOB / 'receipt.json')
    actual = read_json(JOB / 'save-reconciliation-snapshot.json')
    draft = (JOB / 'draft.wiki').read_bytes()
    observed = actual['text'].encode('utf-8')
    if digest(draft) != receipt['draft_sha256'] or observed != draft.removesuffix(b'\n'):
        raise RuntimeError('Unexpected difference; retain unconfirmed receipt without inference.')
    receipt.update(
        status='unconfirmed', reconciliation_at=now(),
        reconciliation_evidence='save-reconciliation-snapshot.json',
        reconciliation_note='One terminal LF missing; exact expected-byte guard not satisfied.',
        observed_revision_id=actual['revision_id'], observed_sha256=actual['sha256'],
        observed_url=actual['url'], automatic_retry_performed=False,
    )
    write_json(JOB / 'receipt.json', receipt)
    status = read_json(JOB / 'status.json')
    status.update(
        status='blocked_exact_save_verification', recorded_at=now(),
        reason='Read-back differs from exact prepared bytes by one terminal LF; no retry.',
        prepare_attempted=True, save_attempted=True,
        pending=['Exact-save verification unsatisfied; retain unconfirmed receipt.'],
        observed_revision_id=actual['revision_id'], observed_url=actual['url'],
        reconciliation='save-reconciliation.md', open_source_issues=17,
        source_issues_memory='source-issues.md',
    )
    write_json(JOB / 'status.json', status)
    print('Mismatch recorded; unconfirmed receipt retained. No write/retry.')
