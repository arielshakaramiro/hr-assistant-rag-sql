"""Answer a POLICY question from retrieved handbook chunks, with citations or an abstain.

Grounding policy (AI_QUALITY.md): the answer is generated ONLY from the retrieved chunks;
when the top similarity is below the threshold the answerer abstains ("not enough in the
handbook") instead of guessing. Each answer carries the citations it used.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.llm import LLMError, chat
from app.core.reason_codes import Confidence
from app.rag.retriever import Retrieved, retrieve

# The model answers from the excerpts only, and emits a sentinel when they don't cover the
# question. The sentinel (not prose-matching) is what the code keys on to mark an abstain,
# so retrieved-but-irrelevant chunks are declined even when their similarity is non-trivial.
NOT_FOUND = "NOT_IN_HANDBOOK"
SYSTEM = f"""You answer an employee's question about company policy using ONLY the provided
handbook excerpts. If the excerpts do not actually answer the question, reply with exactly
{NOT_FOUND} and nothing else — never invent or infer policy that is not stated. Otherwise
answer concisely (1-3 sentences) without mentioning "excerpts" or "context"."""

ABSTAIN_MESSAGE = (
    "I couldn't find this in the handbook, so I won't guess. Try rephrasing, or ask HR directly."
)


@dataclass
class Citation:
    doc_title: str
    section: str
    text: str


@dataclass
class PolicyAnswer:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    confidence: Confidence = Confidence.HIGH
    abstained: bool = False


def answer_policy_question(db: Session, question: str) -> PolicyAnswer:
    hits: list[Retrieved] = retrieve(db, question)
    top = hits[0].similarity if hits else 0.0

    # Weak retrieval → abstain rather than guess.
    if not hits or top < settings.retrieval_min_score:
        return PolicyAnswer(
            answer=ABSTAIN_MESSAGE, citations=[], confidence=Confidence.LOW, abstained=True
        )

    context = "\n\n".join(f"[{h.doc_title} · {h.section}]\n{h.text}" for h in hits)
    user_msg = f"Handbook excerpts:\n{context}\n\nQuestion: {question}"
    try:
        answer = chat(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=220,
        ).strip()
    except LLMError:
        return PolicyAnswer(
            answer="Couldn't generate an answer just now. Please try again.",
            citations=[],
            confidence=Confidence.LOW,
            abstained=False,
        )

    # The model declined: the excerpts don't actually answer the question → abstain.
    if NOT_FOUND in answer:
        return PolicyAnswer(
            answer=ABSTAIN_MESSAGE, citations=[], confidence=Confidence.LOW, abstained=True
        )

    citations = [Citation(h.doc_title, h.section, h.text) for h in hits[:2]]
    return PolicyAnswer(answer=answer, citations=citations, confidence=Confidence.HIGH)
