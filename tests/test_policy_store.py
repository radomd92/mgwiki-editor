"""Durability/locking/schema tests; temporary state, no credentials or network."""

import sqlite3
from pathlib import Path

import pytest

from mgwiki_editor.policy_store import PolicyStore, StateError, identifier


@pytest.fixture
def store(tmp_path: Path) -> PolicyStore:
    result = PolicyStore(tmp_path / "state.sqlite")
    result.create()
    return result


def test_creation_is_explicit_exclusive_and_protected(tmp_path: Path) -> None:
    path = tmp_path / "state.sqlite"
    state = PolicyStore(path)
    assert not path.exists()
    with pytest.raises(StateError, match="missing"):
        state.get("runs", "a")
    state.create()
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        state.create()


def test_records_events_survive_restart_and_hash_verification(store: PolicyStore) -> None:
    with store.transaction() as tx:
        tx.put("runs", "a", {"value": "exact\r\n"}, new=True)
        tx.event(1000, "created", "a", {"source": "évidence"})
        tx.event(1001.5, "updated", "a", {"number": 1})
    restarted = PolicyStore(store.path)
    restarted.verify()
    assert restarted.get("runs", "a") == {"value": "exact\r\n"}
    assert [event["kind"] for event in restarted.events("a")] == ["created", "updated"]


def test_crash_rolls_back_transaction_but_reserved_attempt_committed_first_survives(store):
    with store.transaction() as tx:
        tx.put("attempts", "a", {"status": "unconfirmed"}, new=True)
    with pytest.raises(RuntimeError):
        with store.transaction() as tx:
            tx.put("attempts", "a", {"status": "confirmed"})
            tx.event(1000, "confirmed", "a", {})
            raise RuntimeError("simulated crash")
    assert store.get("attempts", "a")["status"] == "unconfirmed"
    assert store.events() == []
    with pytest.raises(StateError):
        with store.transaction() as tx:
            tx.put("attempts", "a", {"status": "unconfirmed"}, new=True)


def test_concurrent_writer_is_bounded_and_never_cancels_prior_claim(store):
    with store.transaction() as tx:
        tx.put("runs", "a", {"status": "reserved"})
        with pytest.raises(StateError, match="busy"):
            PolicyStore(store.path).get("runs", "a")
    assert store.get("runs", "a")["status"] == "reserved"


@pytest.mark.parametrize("version", [0, 2, 999])
def test_unknown_schema_not_migrated_or_reset(store, version):
    with sqlite3.connect(store.path) as connection:
        connection.execute(f"PRAGMA user_version={version}")
    before = store.path.read_bytes()
    with pytest.raises(StateError, match="schema"):
        store.get("runs", "a")
    assert store.path.read_bytes() == before


def test_corrupt_state_is_preserved(tmp_path):
    path = tmp_path / "state.sqlite"
    path.write_bytes(b"not sqlite")
    with pytest.raises(StateError):
        PolicyStore(path).get("runs", "a")
    assert path.read_bytes() == b"not sqlite"


def test_event_tampering_detected(store):
    with store.transaction() as tx:
        tx.event(1000, "created", "a", {"value": 1})
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE events SET payload='{}'")
    with pytest.raises(StateError, match="chain"):
        store.verify()


def test_symlink_state_refused_without_touching_target(store, tmp_path):
    link = tmp_path / "link.sqlite"
    link.symlink_to(store.path)
    before = store.path.read_bytes()
    with pytest.raises(StateError, match="Symlink"):
        PolicyStore(link).get("runs", "a")
    assert store.path.read_bytes() == before


@pytest.mark.parametrize("value", ["../a", "a/b", "", "/tmp/a", "a\n", "x" * 121, None])
def test_stable_ids_do_not_become_paths(value):
    with pytest.raises(StateError):
        identifier(value)
