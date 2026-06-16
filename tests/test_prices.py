"""Tests for the fetch plumbing in prices.py.

The fetchers themselves are QThreads that hit the network, but the per-ticker
success/failure decision lives in `_safe_call`, which is pure and fast to test.
This is what lets the views tell a genuine empty result apart from a fetch that
errored. `_make_session` is also covered: it must cap the per-request socket
timeout, which is what bounds a blocking call (replacing the old daemon-thread
timeout) so a stalled fetch can't pin the worker thread.
"""
import pytest

from financeguru.prices import _REQUEST_TIMEOUT_S, _safe_call


def test_returns_ok_with_value_on_success():
    ok, value = _safe_call(lambda: 42)
    assert ok is True
    assert value == 42


def test_success_with_none_value_is_still_ok():
    # A function that legitimately returns None (e.g. a delisted ticker) is a
    # success, not a failure — ok must be True so the view doesn't warn.
    ok, value = _safe_call(lambda: None)
    assert ok is True
    assert value is None


def test_exception_is_reported_as_failure():
    def boom():
        raise RuntimeError("network down")

    ok, value = _safe_call(boom)
    assert ok is False
    assert value is None


# _make_session pulls in curl_cffi, which only exists inside `nix develop`.
pytest.importorskip("curl_cffi")


def _capture_request_timeout(monkeypatch, **request_kwargs):
    """Build a session and record the timeout it forwards to the base session."""
    from curl_cffi import requests as creq

    from financeguru.prices import _make_session

    captured = {}

    def fake_request(self, *args, timeout=None, **kwargs):
        captured["timeout"] = timeout
        return "ok"

    monkeypatch.setattr(creq.Session, "request", fake_request)
    session = _make_session()
    session.request("GET", "https://example.com", **request_kwargs)
    return captured["timeout"]


def test_session_caps_an_explicit_timeout(monkeypatch):
    # yfinance passes timeout=30 explicitly; the session must clamp it down so
    # the native socket timeout bounds every request.
    assert _capture_request_timeout(monkeypatch, timeout=30) == _REQUEST_TIMEOUT_S


def test_session_applies_cap_when_no_timeout_given(monkeypatch):
    assert _capture_request_timeout(monkeypatch) == _REQUEST_TIMEOUT_S


def test_session_keeps_a_shorter_timeout(monkeypatch):
    # A caller asking for less than the cap should not be raised up to it.
    assert _capture_request_timeout(monkeypatch, timeout=1.0) == 1.0
