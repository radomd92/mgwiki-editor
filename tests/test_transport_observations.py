"""Verify hooks see real response boundaries, not cache/gate-refusal pseudo-probes."""

import io
import json
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from mgwiki_editor import core
from mgwiki_editor.dictionary_retries import DictionaryRetries
from mgwiki_editor.network import NetworkPolicyError, RequestGate, guarded_send
from mgwiki_editor.observations import Hooks, transport_hooks


def test_cached_dictionary_502_and_exact_nopage_classification(tmp_path):
    seen = []
    retries = DictionaryRetries(tmp_path / "retry.json", clock=lambda: 1000)
    hooks = Hooks(lambda *a: None, seen.append, lambda: 1000, lambda: 1000, "boot")
    def failed(*args, **kwargs):
        raise HTTPError("http://dict", 502, "restart", {}, io.BytesIO(b"restart"))
    with transport_hooks(hooks):
        core.lookup("mg", "rano", opener=failed, retries=retries)
        core.lookup("mg", "rano", opener=failed, retries=retries)
    assert len(seen) == 1 and seen[0].status == 502 and not seen[0].missing
    def missing(*args, **kwargs):
        body = {"type": "error", "status": 502, "details": {"type": "NoPage"}}
        raise HTTPError("http://dict", 502, "bad status", {}, io.BytesIO(json.dumps(body).encode()))
    with transport_hooks(hooks):
        result = core.lookup("mg", "other", opener=missing, retries=retries)
    assert result["status"] == "missing"
    assert seen[-1].missing is True


def test_gate_refusal_is_not_observation_and_503_observed_before_wrapping(tmp_path):
    seen = []
    now = [1000.0]
    gate = RequestGate(tmp_path / "gate.json", clock=lambda: now[0], jitter=lambda *a: 0)
    def send(*args, **kwargs):
        return SimpleNamespace(status_code=503, headers={}, json=lambda: {})
    guarded = guarded_send(send, gate, report=lambda event: None)
    hooks = Hooks(lambda *a: None, seen.append, lambda: now[0], lambda: now[0], "boot")
    prepared = SimpleNamespace(url="https://mg.wikipedia.org/w/api.php", body="action=query")
    with transport_hooks(hooks):
        with pytest.raises(NetworkPolicyError, match="overloaded"):
            guarded(prepared)
        assert len(seen) == 1 and seen[0].status == 503
        with pytest.raises(NetworkPolicyError, match="gate budget"):
            guarded(prepared)
    assert len(seen) == 1


@pytest.mark.parametrize("body,url", [
    ("action=delete", "https://mg.wikipedia.org/w/api.php"),
    ("action=move", "https://mg.wikipedia.org/w/api.php"),
    ("action=edit&action=query", "https://mg.wikipedia.org/w/api.php"),
    ("action=edit", "https://mg.wikipedia.org/w/api.php?action=query"),
])
def test_forbidden_or_duplicate_action_never_sent(tmp_path, body, url):
    def send(*args, **kwargs):
        pytest.fail("Forbidden action reached HTTP adapter")
    guarded = guarded_send(send, RequestGate(tmp_path / "gate.json"), report=lambda event: None)
    with pytest.raises(NetworkPolicyError):
        guarded(SimpleNamespace(url=url, body=body))


@pytest.mark.parametrize("failure", ["before", "after"])
def test_observation_failure_is_fatal_not_retryable(tmp_path, monkeypatch, failure):
    from pywikibot.comms import http
    from pywikibot.exceptions import FatalServerError

    from mgwiki_editor import network
    from mgwiki_editor.policy_store import StateError

    calls = []
    response = SimpleNamespace(status_code=200, headers={}, json=lambda: {"query": {}})
    monkeypatch.setattr(http, "session", SimpleNamespace(send=lambda *a, **k:
                                                        (calls.append(1) or response)))
    gate = RequestGate(tmp_path / "gate.json")
    monkeypatch.setattr(network, "RequestGate", lambda: gate)
    network.install_wikimedia_transport()
    def broken(*args):
        raise StateError("fake journal unavailable")
    hooks = Hooks(broken if failure == "before" else lambda *a: None,
                  broken if failure == "after" else lambda *a: None)
    with transport_hooks(hooks), pytest.raises(FatalServerError, match="resubmission"):
        http.session.send(SimpleNamespace(
            url="https://mg.wikipedia.org/w/api.php", body="action=edit"))
    assert len(calls) == (0 if failure == "before" else 1)


@pytest.mark.parametrize("path,method", [("/jobs", "POST"), ("/translations", "GET"),
                                        ("/wiktionary-pages/en/word", "POST")])
def test_dictionary_transport_never_exposes_wiktionary_write_endpoints(path, method):
    from urllib.request import Request

    from mgwiki_editor.network import dictionary_open

    with pytest.raises(NetworkPolicyError, match="read-only"):
        dictionary_open(Request("http://configured" + path, method=method), timeout=1)


@pytest.mark.parametrize("word", ["../jobs", "..", ".", "%2e%2e%2fjobs", "%252fjobs", "a\\b"])
def test_dictionary_path_encoding_cannot_reach_other_endpoints(word):
    from mgwiki_editor.network import dictionary_word

    with pytest.raises(NetworkPolicyError, match="unsafe"):
        dictionary_word(word)
