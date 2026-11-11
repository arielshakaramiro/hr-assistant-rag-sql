"""Deterministic eval tests: interval math and router output parsing (no model calls)."""

from __future__ import annotations

from app.core.reason_codes import Route
from app.eval.interval import passes_lower, wilson
from app.eval.run import sql_value_matches
from app.router.classifier import _parse


def test_wilson_matches_known_values() -> None:
    iv = wilson(27, 30)
    assert iv.point == 0.9
    assert round(iv.low * 100, 1) == 74.4
    assert round(iv.high * 100, 1) == 96.5


def test_wilson_empty() -> None:
    iv = wilson(0, 0)
    assert iv.low == 0.0 and iv.high == 0.0


def test_passes_lower_gate() -> None:
    # The minimum perfect-run size for a 95% lower bound is 73 (matches `interval.sh minn 95`):
    # 70/70 = 94.8% (fails), 73/73 = 95.0% (passes). 27/30 does not clear 90%.
    assert passes_lower(70, 70, 95.0) is False
    assert passes_lower(73, 73, 95.0) is True
    assert passes_lower(27, 30, 90.0) is False


def test_router_parse_clean_json() -> None:
    d = _parse('{"route": "POLICY", "reason": "a company rule"}')
    assert d.route is Route.POLICY


def test_router_parse_with_fences() -> None:
    d = _parse('```json\n{"route": "DATA", "reason": "own leave"}\n```')
    assert d.route is Route.DATA


def test_router_parse_garbage_falls_back_to_clarify() -> None:
    d = _parse("I think this is about policy maybe")
    assert d.route is Route.CLARIFY


def test_sql_value_matches_checks_values_not_ids() -> None:
    # Matches when the value is a cell value.
    assert sql_value_matches([{"remaining": 7}], ("7",)) is True
    # Does NOT match when the digit only appears in an unrelated id column
    # (this is the verifier finding: substring-on-repr was too loose).
    assert sql_value_matches([{"id": 7, "status": "paid"}], ("450",)) is False
    # Empty rows or empty expectation never match.
    assert sql_value_matches([], ("7",)) is False
    assert sql_value_matches([{"remaining": 7}], ()) is False
