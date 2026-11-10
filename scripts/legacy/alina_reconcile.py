"""Offline reconciliation only: preserve the strict guard failure; never edit."""
import json
from pathlib import Path

from mgwiki_editor.core import artifact_hashes, digest, now

J=Path('runs/alina-iraika-20261105-r1').resolve()


def main():
    receipt=json.loads((J/'receipt.json').read_text(encoding='utf-8'))
    observed=json.loads((J/'save-inspection.json').read_text(encoding='utf-8'))
    proposal=json.loads((J/'proposal.json').read_text(encoding='utf-8'))
    state=json.loads((J/'job.json').read_text(encoding='utf-8'))
    draft=(J/'draft.wiki').read_bytes()
    saved=observed['text'].encode('utf-8')
    assert receipt['status']=='unconfirmed'
    assert artifact_hashes(J)==proposal['artifacts']
    assert receipt['draft_sha256']==digest(draft)==proposal['artifacts']['draft.wiki']
    assert observed['language']=='mg'
    assert observed['title']==receipt['destination']==proposal['destination']
    assert state['sandbox']['revision_id'] is None
    assert observed['revision_id']==1153240
    assert observed['timestamp']=='2026-11-05T18:07:16Z'
    assert observed['timestamp']>=receipt['attempted_at'][:19]+'Z'
    assert draft.endswith(b'\n') and not draft.endswith(b'\n\n')
    assert draft[:-1]==saved
    assert digest(saved)==observed['sha256']=='08bf6e20f34b997f077ecb92c2f7ac98137950ffc01532e9f030030da514471c'
    (J/'receipt-before-reconciliation.json').write_bytes((J/'receipt.json').read_bytes())
    receipt.update(
        status='confirmed_with_terminal_lf_normalization',
        strict_exact_match=False,
        original_guard_result='Save unconfirmed: read-back differs.',
        reconciliation='Paced CLI read confirms exact intended bytes except one terminal LF removed by server; no other changes.',
        saved_sha256=observed['sha256'],
        revision_id=observed['revision_id'],url=observed['url'],verified_at=now(),
        readback_evidence='save-inspection.json',
        no_resubmission=True,
    )
    (J/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
