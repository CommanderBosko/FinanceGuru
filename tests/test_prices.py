"""Tests for the timeout/error plumbing in prices.py.

The fetchers themselves are QThreads that hit the network, but the per-ticker
success/failure decision lives in `_call_with_timeout`, which is pure and fast
to test. This is what lets the views tell a genuine empty result apart from a
fetch that timed out or errored.
"""
import time

from financeguru.prices import _call_with_timeout


def test_returns_ok_with_value_on_success():
    ok, value = _call_with_timeout(lambda: 42, timeout=1.0)
    assert ok is True
    assert value == 42


def test_success_with_none_value_is_still_ok():
    # A function that legitimately returns None (e.g. a delisted ticker) is a
    # success, not a failure — ok must be True so the view doesn't warn.
    ok, value = _call_with_timeout(lambda: None, timeout=1.0)
    assert ok is True
    assert value is None


def test_exception_is_reported_as_failure():
    def boom():
        raise RuntimeError("network down")

    ok, value = _call_with_timeout(boom, timeout=1.0)
    assert ok is False
    assert value is None


def test_timeout_is_reported_as_failure():
    ok, value = _call_with_timeout(lambda: time.sleep(2), timeout=0.05)
    assert ok is False
    assert value is None
