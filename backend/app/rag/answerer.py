"""Answer a POLICY question from retrieved handbook chunks, with citations or an abstain.

Grounding policy (AI_QUALITY.md): the answer is generated ONLY from the retrieved chunks;
when the top similarity is below the threshold the answerer abstains ("not enough in the
handbook") instead of guessing. Each answer carries the citations it used.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.llm import LLMError, chat, chat_stream
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


def _messages(hits: list[Retrieved], question: str) -> list[dict[str, str]]:
    """Build the grounded prompt from retrieved excerpts. Shared by the buffered and streamed
    paths so they ask the model identically."""
    context = "\n\n".join(f"[{h.doc_title} · {h.section}]\n{h.text}" for h in hits)
    user_msg = f"Handbook excerpts:\n{context}\n\nQuestion: {question}"
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_msg}]


def answer_policy_question(db: Session, question: str) -> PolicyAnswer:
    hits: list[Retrieved] = retrieve(db, question)
    top = hits[0].similarity if hits else 0.0

    # Weak retrieval → abstain rather than guess.
    if not hits or top < settings.retrieval_min_score:
        return PolicyAnswer(
            answer=ABSTAIN_MESSAGE, citations=[], confidence=Confidence.LOW, abstained=True
        )

    try:
        answer = chat(_messages(hits, question), max_tokens=220).strip()
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


@dataclass
class PolicyStream:
    """A streamed policy answer: citations/confidence are known up front (from retrieval); the
    answer text arrives via `tokens`. After the generator is exhausted, `abstained` and the final
    `answer` reflect what happened (sentinel → abstain). `tokens` yields display-ready text only
    (the abstain sentinel is never emitted)."""

    citations: list[Citation]
    confidence: Confidence
    tokens: Iterator[str]
    abstained: bool = False
    answer: str = ""


def stream_policy_answer(db: Session, question: str) -> PolicyStream:
    """Stream a grounded policy answer token-by-token, reusing the same retrieval + abstain gate
    and citations as `answer_policy_question`. A short leading buffer lets us detect the
    NOT_IN_HANDBOOK sentinel before emitting anything, so a declined answer becomes a clean
    abstain instead of leaking the sentinel to the user."""
    hits: list[Retrieved] = retrieve(db, question)
    top = hits[0].similarity if hits else 0.0

    if not hits or top < settings.retrieval_min_score:
        return PolicyStream(
            citations=[],
            confidence=Confidence.LOW,
            tokens=iter([ABSTAIN_MESSAGE]),
            abstained=True,
            answer=ABSTAIN_MESSAGE,
        )

    citations = [Citation(h.doc_title, h.section, h.text) for h in hits[:2]]
    result = PolicyStream(citations=citations, confidence=Confidence.HIGH, tokens=iter(()))

    def _gen() -> Iterator[str]:
        # Buffer the first chars so the sentinel can be caught before any text is shown. The
        # sentinel is emitted alone, so once enough non-sentinel text accrues we can flush safely.
        buffer = ""
        flushed = False
        parts: list[str] = []
        try:
            for delta in chat_stream(_messages(hits, question), max_tokens=220):
                parts.append(delta)
                if flushed:
                    yield delta
                    continue
                buffer += delta
                if NOT_FOUND in buffer:
                    # Declined → abstain; drop everything buffered, emit the abstain message.
                    result.citations = []
                    result.confidence = Confidence.LOW
                    result.abstained = True
                    result.answer = ABSTAIN_MESSAGE
                    yield ABSTAIN_MESSAGE
                    return
                # Once the buffer is longer than the sentinel it can't be a (sole) sentinel reply.
                if len(buffer) > len(NOT_FOUND):
                    flushed = True
                    yield buffer
        except LLMError:
            if not flushed and not parts:
                msg = "Couldn't generate an answer just now. Please try again."
                result.answer = msg
                yield msg
                return
        # Stream ended while still buffering (short answer) → flush whatever we held.
        if not flushed and not result.abstained:
            if NOT_FOUND in buffer:
                result.citations = []
                result.confidence = Confidence.LOW
                result.abstained = True
                result.answer = ABSTAIN_MESSAGE
                yield ABSTAIN_MESSAGE
                return
            if buffer:
                yield buffer
        if not result.abstained:
            result.answer = "".join(parts).strip()

    result.tokens = _gen()
    return result
