"""Keep offline tests independent of real Pywikibot credentials and cookies."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_pywikibot_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Never load a user's private Pywikibot configuration during tests."""
    monkeypatch.setenv("PYWIKIBOT_DIR", str(tmp_path))
    monkeypatch.setenv("PYWIKIBOT_NO_USER_CONFIG", "2")
    # Retry/gate tests must never clear or extend the user's real persisted cooldowns.
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
