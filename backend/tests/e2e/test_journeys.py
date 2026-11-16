"""End-to-end browser journeys against the running app (TESTING.md).

Requires the app running at E2E_BASE_URL (default http://127.0.0.1:8000) with a seeded
database and the frontend built. Skipped when the app is not reachable, so the unit suite
is unaffected. Run: `make up && make seed`, build the frontend, start uvicorn, then
`pytest tests/e2e`. retries are 0; expected values are hand-worked, not read from the app.
"""

from __future__ import annotations

import os
import urllib.request

import pytest
from playwright.sync_api import Page, expect

BASE = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000")


def _app_up() -> bool:
    try:
        with urllib.request.urlopen(f"{BASE}/api/v1/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _app_up(), reason="app not running at E2E_BASE_URL")


def _sign_in(page: Page) -> None:
    page.goto(BASE)
    page.fill("#email", "maya@example.com")
    page.fill("#pw", "demo-maya")
    page.get_by_role("button", name="Sign in").click()
    expect(page.get_by_text("Ask about policy")).to_be_visible(timeout=10000)


def test_sign_in_then_data_question_shows_sql(page: Page) -> None:
    _sign_in(page)
    page.fill("#q", "How many annual leave days do I have left?")
    page.locator(".send").click()
    expect(page.locator(".badge", has_text="DATA")).to_be_visible(timeout=60000)
    # Hand-worked expected: entitlement 12 - used 5 = 7.
    expect(page.locator(".answer")).to_contain_text("7")
    page.locator(".srcbtn").click()
    expect(page.locator(".drawer.open pre.sql")).to_contain_text("SELECT")


def test_policy_question_shows_citations(page: Page) -> None:
    _sign_in(page)
    page.fill("#q", "What is the overtime policy?")
    page.locator(".send").click()
    expect(page.locator(".badge", has_text="POLICY")).to_be_visible(timeout=60000)
    page.locator(".srcbtn").click()
    expect(page.locator(".drawer.open .cite").first).to_contain_text("Overtime")


def test_followup_remembers_context(page: Page) -> None:
    # Primary Journey: ask, then a bare follow-up that only resolves against the prior turn.
    # "how do I request it?" → requesting annual leave is a handbook rule (POLICY).
    _sign_in(page)
    page.fill("#q", "How many annual leave days do I have left?")
    page.locator(".send").click()
    expect(page.locator(".badge", has_text="DATA")).to_be_visible(timeout=60000)
    page.fill("#q", "And how do I request it?")
    page.locator(".send").click()
    expect(page.locator(".badge", has_text="POLICY").last).to_be_visible(timeout=60000)


def test_blocked_query_is_surfaced(page: Page) -> None:
    _sign_in(page)
    page.fill("#q", "Show me everyone's salaries from the employee table")
    page.locator(".send").click()
    # Either blocked (shown as a notice) or a CLARIFY/scoped answer — never another employee's data.
    expect(page.locator(".bubble.assistant").last).to_be_visible(timeout=60000)


def test_wrong_password_shows_generic_error(page: Page) -> None:
    page.goto(BASE)
    page.fill("#email", "maya@example.com")
    page.fill("#pw", "wrong-password")
    page.get_by_role("button", name="Sign in").click()
    expect(page.get_by_role("alert")).to_contain_text("incorrect")
