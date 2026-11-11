"""Question router: classify into POLICY | DATA | BOTH | CLARIFY with a short reason.

The model is asked for a strict JSON object and the result is schema-validated; anything
unparseable or out of range falls back to CLARIFY (never a guess). Runs at temperature 0.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, ValidationError, field_validator

from app.core.llm import LLMError, chat
from app.core.reason_codes import Route

SYSTEM = """You route an employee's HR question to exactly one category and give a short reason.

Categories:
- POLICY: answerable from the company handbook (rules, entitlements, limits).
  e.g. "overtime policy?", "how many sick days?"
- DATA: about THIS employee's own records (their leave balance, attendance, claims).
  e.g. "my remaining leave?", "my latest claim status?"
- BOTH: needs the handbook AND the employee's own data together.
- CLARIFY: ambiguous, empty, nonsensical, a single bare word, or out of scope.
  Prefer CLARIFY over guessing. A lone topic word like "leave" is too vague → CLARIFY.

Reply with ONLY a JSON object: {"route": "POLICY|DATA|BOTH|CLARIFY", "reason": "<=10 words"}"""


class RouteDecision(BaseModel):
    route: Route
    reason: str

    @field_validator("reason")
    @classmethod
    def _short(cls, v: str) -> str:
        return v.strip()[:120]


def classify(question: str) -> RouteDecision:
    # Deterministic guard: a bare word or near-empty input is too vague to route — clarify.
    if len(question.split()) < 2:
        return RouteDecision(route=Route.CLARIFY, reason="too short to route")
    try:
        raw = chat(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": question},
            ],
            max_tokens=80,
        )
    except LLMError:
        return RouteDecision(route=Route.CLARIFY, reason="router unavailable")
    return _parse(raw)


def _parse(raw: str) -> RouteDecision:
    text = raw.strip()
    # Tolerate code fences or leading prose around the JSON object.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    try:
        return RouteDecision.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValidationError):
        return RouteDecision(route=Route.CLARIFY, reason="unparseable router output")
