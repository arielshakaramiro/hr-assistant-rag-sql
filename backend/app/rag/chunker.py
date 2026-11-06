"""Split the policy handbook into retrievable chunks, one per leaf section.

Each chunk keeps its document title and section heading so citations can name them
(APP_FLOW: POLICY answers cite doc title + section). Sections are the natural unit here;
a section longer than ``max_chars`` is split on blank lines.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class Chunk:
    title: str
    section: str
    ordinal: int
    text: str


def chunk_markdown(doc_title: str, markdown: str, max_chars: int = 900) -> list[Chunk]:
    """Chunk by the deepest-heading sections. The section heading is prepended to each chunk's
    text (it improves retrieval and anchors the citation) and also returned on the Chunk.
    A chunk before the first section heading (the preamble) is skipped as non-citable noise.
    """
    chunks: list[Chunk] = []
    section: str | None = None  # None until the first citable heading
    buf: list[str] = []
    ordinal = 0

    def flush() -> None:
        nonlocal ordinal, buf
        body = "\n".join(buf).strip()
        buf = []
        if not body or section is None:
            return  # skip the preamble (no section yet)
        for piece in _split(body, max_chars):
            text = f"{section}\n{piece}"
            chunks.append(Chunk(doc_title, section, ordinal, text))
            ordinal += 1

    for line in markdown.splitlines():
        m = HEADING.match(line)
        # A deeper heading (### or more) starts a new citable section.
        if m and len(m.group(1)) >= 3:
            flush()
            section = m.group(2).strip()
            continue
        buf.append(line)
    flush()
    return chunks


def _split(body: str, max_chars: int) -> list[str]:
    if len(body) <= max_chars:
        return [body]
    parts, cur = [], ""
    for para in body.split("\n\n"):
        if len(cur) + len(para) + 2 > max_chars and cur:
            parts.append(cur.strip())
            cur = ""
        cur += para + "\n\n"
    if cur.strip():
        parts.append(cur.strip())
    return parts
