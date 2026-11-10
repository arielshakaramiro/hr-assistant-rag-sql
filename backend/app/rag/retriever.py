"""Retrieve policy chunks by vector similarity, with the score so the answerer can abstain.

Cosine distance from pgvector is converted to a similarity (1 - distance). When the best
similarity is below the configured threshold the caller abstains rather than guess
(AI_QUALITY.md grounding policy).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import PolicyChunk, PolicyDoc
from app.rag.embedder import embed_one


@dataclass(frozen=True)
class Retrieved:
    doc_title: str
    section: str
    text: str
    similarity: float


def retrieve(db: Session, question: str, k: int = 4) -> list[Retrieved]:
    vec = embed_one(question)
    # Scan more ivfflat lists so small corpora still return the full k candidates.
    db.execute(text("SET LOCAL ivfflat.probes = 10"))
    distance = PolicyChunk.embedding.cosine_distance(vec)
    rows = db.execute(
        select(PolicyDoc.title, PolicyChunk.section, PolicyChunk.text, distance.label("d"))
        .join(PolicyDoc, PolicyDoc.id == PolicyChunk.doc_id)
        .order_by("d")
        .limit(k)
    ).all()
    return [
        Retrieved(doc_title=title, section=section, text=text, similarity=1.0 - float(d))
        for title, section, text, d in rows
    ]
