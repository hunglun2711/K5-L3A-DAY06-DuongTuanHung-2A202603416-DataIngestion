"""Implement fixed-size and structure-aware chunking with metadata preservation."""
from __future__ import annotations

import re

from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Split page text into fixed-size overlapping character windows."""
    if size <= 0:
        raise ValueError("size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must satisfy 0 <= overlap < size")

    text = page.text.strip()
    if not text:
        return []

    chunks: list[Chunk] = []
    step = size - overlap
    start = 0
    idx = 0
    while start < len(text):
        end = min(start + size, len(text))
        piece = text[start:end].strip()
        if piece:
            meta = {
                **page.metadata,
                "chunk_strategy": "fixed_size",
                "chunk_index": idx,
                "char_start": start,
                "char_end": end,
                "char_count": len(piece),
            }
            chunks.append(
                Chunk(
                    chunk_id=f"{page.document_id}_p{page.page:02d}_fix_{idx:02d}",
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=piece,
                    metadata=meta,
                )
            )
            idx += 1
        if end >= len(text):
            break
        start += step
    return chunks


def _looks_like_heading(block: str) -> bool:
    if len(block) > 65 or "\n" in block:
        return False
    if block.endswith((".", "!", "?", ",", ";", ":")):
        return False
    if block.startswith(("•", "-", "*")) or re.match(r"^(?:[a-d]\.|\d+\s+\.)", block):
        return False
    return True


def _split_oversized_paragraph(para: str, max_size: int) -> list[str]:
    if len(para) <= max_size:
        return [para]
    sentences = re.split(r"(?<=[.!?])\s+", para)
    parts: list[str] = []
    buf = ""
    for sent in sentences:
        if not sent:
            continue
        if len(sent) > max_size:
            if buf:
                parts.append(buf.strip())
                buf = ""
            words = sent.split(" ")
            w_buf = ""
            for w in words:
                candidate = f"{w_buf} {w}".strip() if w_buf else w
                if len(candidate) <= max_size:
                    w_buf = candidate
                else:
                    if w_buf:
                        parts.append(w_buf)
                    w_buf = w[:max_size]
            if w_buf:
                parts.append(w_buf)
        else:
            candidate = f"{buf} {sent}".strip() if buf else sent
            if len(candidate) <= max_size:
                buf = candidate
            else:
                if buf:
                    parts.append(buf.strip())
                buf = sent
    if buf:
        parts.append(buf.strip())
    return parts


def by_paragraph(page: DocumentPage, max_size: int = 800) -> list[Chunk]:
    """Group headings and paragraphs up to max_size; split oversized blocks at sentences."""
    if max_size <= 0:
        raise ValueError("max_size must be positive")

    text = page.text.strip()
    if not text:
        return []

    raw_blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    units: list[tuple[str | None, str]] = []
    active_heading: str | None = None

    i = 0
    while i < len(raw_blocks):
        block = raw_blocks[i]
        if _looks_like_heading(block):
            active_heading = block
            if i + 1 < len(raw_blocks) and not _looks_like_heading(raw_blocks[i + 1]):
                combined = f"{block}\n{raw_blocks[i + 1]}"
                for part in _split_oversized_paragraph(combined, max_size):
                    units.append((active_heading, part))
                i += 2
                continue
            units.append((active_heading, block))
        else:
            for part in _split_oversized_paragraph(block, max_size):
                units.append((active_heading, part))
        i += 1

    grouped: list[str] = []
    current = ""
    for heading, unit in units:
        if not current:
            if heading and not unit.startswith(heading):
                prefixed = f"[{heading}] {unit}"
                current = prefixed if len(prefixed) <= max_size else unit
            else:
                current = unit
            continue
        candidate = f"{current}\n\n{unit}"
        if len(candidate) <= max_size:
            current = candidate
        else:
            grouped.append(current)
            if heading and not unit.startswith(heading):
                prefixed = f"[{heading}] {unit}"
                current = prefixed if len(prefixed) <= max_size else unit
            else:
                current = unit
    if current:
        grouped.append(current)

    chunks: list[Chunk] = []
    for idx, piece in enumerate(grouped):
        meta = {
            **page.metadata,
            "chunk_strategy": "by_paragraph",
            "chunk_index": idx,
            "char_count": len(piece),
        }
        chunks.append(
            Chunk(
                chunk_id=f"{page.document_id}_p{page.page:02d}_para_{idx:02d}",
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=piece,
                metadata=meta,
            )
        )
    return chunks
