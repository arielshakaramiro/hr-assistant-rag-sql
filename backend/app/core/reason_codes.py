"""Shared enums — the single source of truth imported by backend and (generated) frontend.

API.md §7 documents these lists; this module is their canonical home.
No other module redefines them.
"""

from __future__ import annotations

from enum import StrEnum


class Route(StrEnum):
    POLICY = "POLICY"
    DATA = "DATA"
    BOTH = "BOTH"
    CLARIFY = "CLARIFY"


class Outcome(StrEnum):
    SUCCESS = "success"
    ABSTAINED = "abstained"
    BLOCKED = "blocked"
    ERROR = "error"


class Confidence(StrEnum):
    HIGH = "high"
    LOW = "low"


class ReasonCode(StrEnum):
    """Guardrail block reasons for generated SQL."""

    NON_SELECT = "NON_SELECT"
    MULTIPLE_STATEMENTS = "MULTIPLE_STATEMENTS"
    DISALLOWED_TABLE = "DISALLOWED_TABLE"
    DISALLOWED_COLUMN = "DISALLOWED_COLUMN"
    CROSS_EMPLOYEE_REF = "CROSS_EMPLOYEE_REF"
    MISSING_EMPLOYEE_SCOPE = "MISSING_EMPLOYEE_SCOPE"
    TIMEOUT = "TIMEOUT"
    ROW_LIMIT = "ROW_LIMIT"
    PARSE_ERROR = "PARSE_ERROR"


class ErrorCode(StrEnum):
    UNAUTHENTICATED = "UNAUTHENTICATED"
    INVALID_INPUT = "INVALID_INPUT"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL = "INTERNAL"
