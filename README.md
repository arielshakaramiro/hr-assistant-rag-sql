# HR Assistant — Policy & Employee Data

An employee-facing HR assistant that answers questions about **company policy** (RAG over a
handbook) and an employee's **own leave, attendance and claims** (a guarded SQL agent), with
strict per-employee access control. Every answer shows its sources — the policy citations, or
the exact SQL that ran and its result.

> All data in this project is **synthetic**. It is a portfolio demonstration, not a product
> handling real employee records.

## The problem → why it matters → the approach → the result

- **Problem.** HR teams field the same questions over and over — remaining leave, overtime
  rules, claim status — while the answers already live in a handbook or a database.
- **Impact.** Repetitive questions cost HR time, and employees wait for answers that could be
  self-served. Existing tools answer policy *or* query data, rarely both, and rarely show their
  work; combining per-employee data access with cited policy answers in one open, self-hostable
  app is uncommon.
- **Approach.** One assistant routes each question to a policy path, a data path, both, or a
  clarify path. Policy answers come only from retrieved handbook text and cite it; data answers
  come from a read-only SQL agent that is confined to the signed-in employee by database
  row-level security. Both paths show their sources.
- **Result.** On a synthetic English handbook and dataset, measured on a **free, local model**
  (qwen2.5:7b via Ollama): router 100%, grounded policy answers 100%, with **zero data leaks
  across an independent adversarial attack** (see below). Runs at ~$0 on free-tier
  infrastructure.

## What makes it more than a chatbot

- **Measured evaluation.** A golden set + harness reports accuracy with sample size and a 95%
  confidence interval — not a vibe. `make eval` reproduces the numbers.
- **Row-level security, enforced in the database.** An employee can read only their own rows,
  guaranteed by PostgreSQL row-level-security policies and a read-only role — not by a prompt.
  An unrestricted or injected query still returns only the caller's data.
- **SQL guardrails you can see.** Generated SQL is SELECT-only, allowlisted, single-statement,
  runs under a timeout and row cap — and the UI shows the query that ran (or the one that was
  blocked, with the reason).
- **Transparent routing.** Each answer shows which path was chosen and why.
- **Grounded, with an "I don't know".** Policy answers cite the handbook section; when the
  handbook doesn't cover a question, the assistant abstains instead of inventing policy.
- **Observability.** Per-query latency, cost and outcome are logged (metadata only — no stored
  question text unless you rate an answer).

## Measured quality

Measured on the free local model (qwen2.5:7b), development golden set, 95% Wilson intervals.
First-run numbers on an author-written set are weak evidence on their own; the adversarial round
below is the stronger check. The golden set is small (portfolio scale), so the lower interval
bounds do not yet clear the target thresholds — the numbers are reported honestly with their n.

| Metric | Result | 95% interval | Target |
| --- | --- | --- | --- |
| Router accuracy | 19/19 = 100% | 83.2–100% | ≥ 90% |
| Policy grounded accuracy (cite or abstain) | 12/12 = 100% | 75.7–100% | ≥ 85% |
| SQL execution-accuracy | 4/6 = 67% | 30.0–90.3% | ≥ 85% |
| **Row-level isolation under attack** | **0 leaks / 27 adversarial + 4 isolation tests** | leak-rate upper bound 12.5% | **0 leaks** |

**Adversarial round.** 54 independent attack cases — written by a different model family that
never saw the policy, golden set, or thresholds — were run against the live app: 52/54 passed,
and **every one of the 27 data-exfiltration attempts** (prompt injection, admin-mode override,
"pretend RLS is disabled", SQL injection with `DROP`/`UNION`/`OR 1=1`, a DAN jailbreak, base64)
**returned only the caller's own rows or was blocked.** The guarantee is the database mechanism;
the cases are evidence (`python -m app.eval.attacker` re-runs them). The two misses were routing
nuances with no security impact.

The free local model stumbles on a couple of ambiguously-phrased aggregate SQL questions (the
4/6); clear questions are reliable, and a stronger production model is expected to improve this.

## Stack

- **Backend:** FastAPI (Python 3.12), SQLAlchemy + Alembic, PostgreSQL 16 with `pgvector`.
- **AI:** a question router, RAG over pgvector with local `sentence-transformers` embeddings, a
  guarded read-only SQL agent. Model via any OpenAI-compatible endpoint — local Ollama for
  development/eval, a hosted free tier (Groq Llama 3.3 70B) for the deployed demo.
- **Frontend:** Vite + React + TypeScript, built to static files and served by the backend from
  **one Docker container**. Dark/light, keyboard-accessible, self-hosted fonts.

## Getting started

Prerequisites: Docker, Python 3.12, Node 22. (For local AI eval: [Ollama](https://ollama.com)
with `qwen2.5:7b` pulled.)

```bash
# 1. Start PostgreSQL + pgvector
make up

# 2. Backend
cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'
cp .env.example .env            # defaults point at the local DB and Ollama
cd .. && make seed              # synthetic data + handbook ingestion

# 3. Frontend (build once; the backend serves it)
cd frontend && npm install && npm run build && cd ..

# 4. Run
cd backend && . .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000
# open http://127.0.0.1:8000
```

Or the whole thing in one container:

```bash
docker build -t hr-assistant .
docker run --rm -p 8000:8000 --env-file backend/.env hr-assistant
```

**Demo accounts** (synthetic): `maya@example.com` / `demo-maya` · `adi@example.com` / `demo-adi`.

## Commands

| Command | What it does |
| --- | --- |
| `make up` / `make down` | PostgreSQL + pgvector via Docker |
| `make seed` | Load synthetic data and ingest the handbook |
| `make check` | Lint, format, typecheck, and tests (the commit gate) |
| `make eval` | Run the golden set and print metrics with intervals |

## Testing

`make check` runs the unit/integration suite (including the row-level isolation tests). Browser
journeys live in `backend/tests/e2e` and run against a running app. Design checks (contrast,
axe-core, three widths) pass on the shipped screens.

## Known limits

- English only; synthetic data; not validated on real HR records.
- Free-tier hosting cold-starts (the first request after idle is slow); the demo video is
  recorded warm.
- The golden set is portfolio-scale, so headline rates are reported with their intervals rather
  than as point claims; SQL accuracy on the free local model dips on ambiguous aggregate
  questions.
- Single-process rate limiting; a real multi-instance deployment would use a shared store.

## Continuous integration

The CI workflow is provided at `.github/ci-pending/ci.yml.txt`. To activate it, move it to
`.github/workflows/ci.yml` and commit (adding a workflow requires the `workflow` token scope).
It runs the deterministic checks on PostgreSQL and builds the frontend.

## License

MIT (see LICENSE).
