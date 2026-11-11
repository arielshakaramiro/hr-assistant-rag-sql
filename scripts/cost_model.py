"""Cost model for the HR Assistant.

Pure arithmetic over the usage assumptions in prices.toml. The budget guard in the
app imports PER_TASK_CEILING_USD and DAILY_SPEND_CAP_USD from here (one source of
truth), and a test ties the guard's constants to this computation.

All prices/quotas come from prices.toml, which carries a source URL + date per line
(filled in Phase 3 from provider docs). A figure with no source is marked UNVERIFIED
there and must not silently drive a gate.

Run: python scripts/cost_model.py   (prints the per-case table)
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG = Path(__file__).with_name("prices.toml")


@dataclass(frozen=True)
class Case:
    name: str
    queries_per_day: float


def load_config() -> dict:
    with CONFIG.open("rb") as fh:
        return tomllib.load(fh)


def per_task_cost_usd(cfg: dict) -> float:
    """Estimated $ per user question.

    A question costs up to `llm_calls_per_query` chat calls (router + RAG and/or SQL)
    plus `embed_calls_per_query` embedding calls (cached). On a free tier within quota
    this is ~0; the config still carries the per-1k-token prices so an overage estimate
    is possible.
    """
    m = cfg["model"]
    tokens_in = m["avg_tokens_in"] * m["llm_calls_per_query"]
    tokens_out = m["avg_tokens_out"] * m["llm_calls_per_query"]
    chat = (tokens_in / 1000) * m["price_in_per_1k"] + (tokens_out / 1000) * m["price_out_per_1k"]
    embed = (m["embed_tokens_per_query"] / 1000) * m["embed_price_per_1k"] * m["embed_calls_per_query"]
    return round(chat + embed, 6)


def monthly_fixed_usd(cfg: dict) -> float:
    f = cfg["fixed_monthly"]
    return round(sum(float(v) for v in f.values()), 2)


def monthly_total_usd(cfg: dict, case: Case) -> float:
    variable = per_task_cost_usd(cfg) * case.queries_per_day * 30
    return round(variable + monthly_fixed_usd(cfg), 2)


def per_task_ceiling_usd(cfg: dict) -> float:
    """Monthly budget / expected tasks per month (kill criterion K1 tests against this)."""
    b = cfg["budget"]
    expected = cfg["cases"]["expected"] * 30
    if expected <= 0:
        return 0.0
    return round(b["monthly_budget_usd"] / expected, 6)


def daily_spend_cap_usd(cfg: dict) -> float:
    return float(cfg["budget"]["daily_spend_cap_usd"])


def hard_ceiling_usd(cfg: dict) -> float:
    """Daily cap * days + evaluation cost, shown next to the expected monthly total."""
    b = cfg["budget"]
    return round(daily_spend_cap_usd(cfg) * 30 + b.get("eval_cost_usd_per_month", 0.0), 2)


# Exported for the app's budget guard (single source of truth).
def _cfg() -> dict:
    return load_config()


try:
    _c = _cfg()
    PER_TASK_CEILING_USD = per_task_ceiling_usd(_c)
    DAILY_SPEND_CAP_USD = daily_spend_cap_usd(_c)
except FileNotFoundError:  # config not filled yet (pre-Phase-3)
    PER_TASK_CEILING_USD = 0.0
    DAILY_SPEND_CAP_USD = 0.0


def main() -> None:
    cfg = load_config()
    cases = [Case(k, float(v)) for k, v in cfg["cases"].items()]
    print(f"per-task cost: ${per_task_cost_usd(cfg):.6f}")
    print(f"fixed monthly: ${monthly_fixed_usd(cfg):.2f}")
    print(f"per-task ceiling (K1): ${per_task_ceiling_usd(cfg):.6f}")
    print(f"daily spend cap: ${daily_spend_cap_usd(cfg):.2f}")
    print(f"hard ceiling: ${hard_ceiling_usd(cfg):.2f}")
    print("case           queries/day   monthly total")
    for c in cases:
        print(f"{c.name:<14} {c.queries_per_day:<13.0f} ${monthly_total_usd(cfg, c):.2f}")


if __name__ == "__main__":
    main()
