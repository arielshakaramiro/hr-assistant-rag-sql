"""SQLAlchemy models. See docs/DATABASE.md for the data model and rules.

All employee data is synthetic. Every per-employee table carries an indexed employee_id,
which drives both the foreign key and the row-level access scope.
"""

from __future__ import annotations

from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

EMBED_DIM = 384  # bge-small-en-v1.5 / all-MiniLM-L6-v2 output dimension


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Employee(TimestampMixin, Base):
    __tablename__ = "employee"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(80))
    # role reserved for the backlog HR-admin feature; v1 only uses "employee".
    role: Mapped[str] = mapped_column(String(20), default="employee")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    leave_records: Mapped[list[LeaveRecord]] = relationship(back_populates="employee")
    leave_balances: Mapped[list[LeaveBalance]] = relationship(back_populates="employee")
    attendance: Mapped[list[AttendanceRecord]] = relationship(back_populates="employee")
    claims: Mapped[list[Claim]] = relationship(back_populates="employee")


class LeaveBalance(TimestampMixin, Base):
    __tablename__ = "leave_balance"
    __table_args__ = (UniqueConstraint("employee_id", "year", name="uq_leave_balance_emp_year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"), index=True)
    year: Mapped[int] = mapped_column(Integer)
    entitlement_days: Mapped[int] = mapped_column(Integer)
    used_days: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee: Mapped[Employee] = relationship(back_populates="leave_balances")


class LeaveRecord(TimestampMixin, Base):
    __tablename__ = "leave_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"), index=True)
    leave_type: Mapped[str] = mapped_column(String(20))  # annual | sick | unpaid
    start_date: Mapped[date] = mapped_column()
    end_date: Mapped[date] = mapped_column()
    days: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))  # approved | pending | rejected

    employee: Mapped[Employee] = relationship(back_populates="leave_records")


class AttendanceRecord(TimestampMixin, Base):
    __tablename__ = "attendance_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"), index=True)
    work_date: Mapped[date] = mapped_column()
    status: Mapped[str] = mapped_column(String(20))  # present | late | absent | leave | holiday
    minutes_late: Mapped[int] = mapped_column(Integer, default=0)

    employee: Mapped[Employee] = relationship(back_populates="attendance")


class Claim(TimestampMixin, Base):
    __tablename__ = "claim"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"), index=True)
    claim_type: Mapped[str] = mapped_column(String(20))  # medical | transport | meal | other
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="IDR")
    status: Mapped[str] = mapped_column(String(20))  # submitted | approved | rejected | paid

    employee: Mapped[Employee] = relationship(back_populates="claims")


class PolicyDoc(TimestampMixin, Base):
    __tablename__ = "policy_doc"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    section: Mapped[str] = mapped_column(String(120))
    source_path: Mapped[str] = mapped_column(String(300))

    chunks: Mapped[list[PolicyChunk]] = relationship(back_populates="doc")


class PolicyChunk(TimestampMixin, Base):
    __tablename__ = "policy_chunk"
    __table_args__ = (
        Index(
            "ix_policy_chunk_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"lists": 10},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[int] = mapped_column(ForeignKey("policy_doc.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    # The handbook section this chunk belongs to (e.g. "§4.3 Overtime pay"), for precise citations.
    section: Mapped[str] = mapped_column(String(160), default="")
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM))
    token_count: Mapped[int] = mapped_column(Integer, default=0)

    doc: Mapped[PolicyDoc] = relationship(back_populates="chunks")


class Session(Base):
    __tablename__ = "session"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256 of the token
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Feedback(TimestampMixin, Base):
    """The ONLY place question/answer text is stored — created on an explicit thumbs rating."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"), index=True)
    question_text: Mapped[str] = mapped_column(Text)
    answer_text: Mapped[str] = mapped_column(Text)
    route: Mapped[str] = mapped_column(String(10))
    rating: Mapped[str] = mapped_column(String(4))  # up | down


class QueryMetric(Base):
    """Per-query metadata only — never question/answer text."""

    __tablename__ = "query_metric"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    route: Mapped[str] = mapped_column(String(10))
    latency_ms: Mapped[int] = mapped_column(Integer)
    est_cost_usd: Mapped[float] = mapped_column(Numeric(10, 6), default=0)
    outcome: Mapped[str] = mapped_column(String(12))  # success | abstained | blocked | error
