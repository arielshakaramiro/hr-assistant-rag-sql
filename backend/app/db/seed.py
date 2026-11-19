"""Seed synthetic data and ingest the policy handbook. Development/demo only (DATABASE.md §7).

Creates at least two distinct employees so row-level isolation can be tested, with
deterministic demo passwords, and ingests every file under data/policy into chunks+embeddings.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import select, text

from app.core.security import hash_password
from app.db.models import (
    AttendanceRecord,
    Claim,
    Employee,
    LeaveBalance,
    LeaveRecord,
    PolicyChunk,
    PolicyDoc,
)
from app.db.session import SessionLocal
from app.rag.chunker import chunk_markdown
from app.rag.embedder import embed

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "policy"

# Two distinct employees (isolation tests rely on them) plus one HR admin for the team
# dashboard. Demo passwords go in the README. Each row carries an explicit role.
EMPLOYEES = [
    {
        "email": "maya@example.com",
        "pw": "demo-maya",
        "name": "Maya Putri",
        "dept": "Engineering",
        "role": "employee",
    },
    {
        "email": "adi@example.com",
        "pw": "demo-adi",
        "name": "Adi Santoso",
        "dept": "Finance",
        "role": "employee",
    },
    {
        "email": "hr@example.com",
        "pw": "demo-hr",
        "name": "Rina Hartono",
        "dept": "People",
        "role": "hr_admin",
    },
]


def _seed_employees(db: object) -> list[Employee]:
    rows: list[Employee] = []
    for e in EMPLOYEES:
        emp = Employee(
            email=e["email"],
            password_hash=hash_password(e["pw"]),
            full_name=e["name"],
            department=e["dept"],
            role=e["role"],
        )
        db.add(emp)  # type: ignore[attr-defined]
        rows.append(emp)
    db.flush()  # type: ignore[attr-defined]
    return rows


def _seed_records(db: object, emps: list[Employee]) -> None:
    # Maya/Adi carry the hand-worked golden numbers and the isolation pair; the admin (Rina)
    # only needs a leave_balance row so the roster has three entries.
    maya, adi, rina = emps
    # Maya: entitlement 12, used 5 → 7 remaining (the golden-set hand-worked number).
    db.add_all(  # type: ignore[attr-defined]
        [
            LeaveBalance(employee_id=maya.id, year=2026, entitlement_days=12, used_days=5),
            LeaveBalance(employee_id=adi.id, year=2026, entitlement_days=12, used_days=2),
            LeaveBalance(employee_id=rina.id, year=2026, entitlement_days=12, used_days=0),
            LeaveRecord(
                employee_id=maya.id,
                leave_type="annual",
                start_date=date(2026, 3, 12),
                end_date=date(2026, 3, 14),
                days=3,
                status="approved",
            ),
            LeaveRecord(
                employee_id=maya.id,
                leave_type="sick",
                start_date=date(2026, 5, 2),
                end_date=date(2026, 5, 2),
                days=1,
                status="approved",
            ),
            LeaveRecord(
                employee_id=maya.id,
                leave_type="annual",
                start_date=date(2026, 6, 20),
                end_date=date(2026, 6, 20),
                days=1,
                status="pending",
            ),
            AttendanceRecord(
                employee_id=maya.id, work_date=date(2026, 11, 3), status="present", minutes_late=0
            ),
            AttendanceRecord(
                employee_id=maya.id, work_date=date(2026, 11, 4), status="late", minutes_late=12
            ),
            AttendanceRecord(
                employee_id=maya.id, work_date=date(2026, 11, 5), status="present", minutes_late=0
            ),
            Claim(
                employee_id=maya.id,
                claim_type="medical",
                amount=450000,
                currency="IDR",
                status="paid",
            ),
            Claim(
                employee_id=maya.id,
                claim_type="transport",
                amount=120000,
                currency="IDR",
                status="approved",
            ),
            # Adi's own rows — must never surface for Maya.
            Claim(
                employee_id=adi.id,
                claim_type="meal",
                amount=85000,
                currency="IDR",
                status="submitted",
            ),
            AttendanceRecord(
                employee_id=adi.id, work_date=date(2026, 11, 4), status="present", minutes_late=0
            ),
        ]
    )


def _ingest_policies(db: object) -> int:
    n = 0
    for path in sorted(DATA_DIR.glob("*.md")):
        title = path.stem.replace("_", " ").title()
        doc = PolicyDoc(title="Employee Handbook", section=title, source_path=str(path.name))
        db.add(doc)  # type: ignore[attr-defined]
        db.flush()  # type: ignore[attr-defined]
        chunks = chunk_markdown("Employee Handbook", path.read_text())
        vectors = embed([c.text for c in chunks])
        for c, vec in zip(chunks, vectors, strict=True):
            db.add(  # type: ignore[attr-defined]
                PolicyChunk(
                    doc_id=doc.id,
                    ordinal=c.ordinal,
                    section=c.section,
                    text=c.text,
                    embedding=vec,
                    token_count=len(c.text.split()),
                )
            )
            n += 1
    return n


def seed(with_policies: bool = True) -> None:
    """Seed synthetic employees + records and (by default) ingest the policy handbook.

    with_policies=False skips the handbook ingestion, which is the only step that loads the
    embedding model. CI uses that to seed the data its non-model tests need (auth/admin/me/
    isolation) without downloading model weights; the demo and RAG tests use the default.
    """
    with SessionLocal() as db:
        # Idempotent: truncate (resets identity sequences so demo IDs are stable) then reseed.
        db.execute(
            text(
                "TRUNCATE policy_chunk, policy_doc, claim, attendance_record, leave_record, "
                "leave_balance, feedback, session, employee RESTART IDENTITY CASCADE"
            )
        )
        db.commit()

        emps = _seed_employees(db)
        _seed_records(db, emps)
        n_chunks = _ingest_policies(db) if with_policies else 0
        db.commit()

        first_id = db.scalar(select(Employee.id).limit(1))
        print(f"seeded {len(emps)} employees, {n_chunks} policy chunks (first id={first_id})")


if __name__ == "__main__":
    import sys

    # `python -m app.db.seed --no-policies` skips handbook ingestion (no embedding model).
    seed(with_policies="--no-policies" not in sys.argv)
