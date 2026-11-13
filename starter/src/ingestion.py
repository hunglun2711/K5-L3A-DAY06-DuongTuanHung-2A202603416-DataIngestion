"""Read and normalize source data while keeping full page-level traceability."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from .models import DocumentPage

_FOOTER_RE = re.compile(
    r"^(?:\d+\s+\d+\s+•\s+.*|Access for free at openstax\.org)$",
    re.IGNORECASE,
)
_HEADING_RE = re.compile(
    r"^(?:\d+\.\d+\s+[A-Z].*|Learning [Oo]bjectives|CHECKPOINT|CONCEPTS IN PRACTICE|"
    r"EXAMPLE\s+\d+\.\d+|Chapter Outline|Introduction|[A-Z][A-Za-z0-9 ,()/'\"-]{2,55})$"
)


@dataclass
class IngestionResult:
    """Container for loaded content pages and excluded/error page logs."""

    pages: list[DocumentPage] = field(default_factory=list)
    excluded_pages: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)


def _is_heading_line(line: str) -> bool:
    """Heuristic check for OpenStax section/subsection headings and block labels."""
    if not line or len(line) > 65:
        return False
    if line.endswith((".", ",", ";", ":")):
        return False
    if line.startswith(("•", "-", "*", "a.", "b.", "c.", "d.")):
        return False
    if re.match(r"^\d+\s+\.", line):
        return False
    if "=" in line or "(" in line and ")" in line and not line.startswith("EXAMPLE"):
        return False
    return bool(_HEADING_RE.match(line))


def normalize_text(text: str) -> str:
    """Normalize Unicode, remove PDF running footers, and reconstruct paragraph breaks."""
    normalized = unicodedata.normalize("NFC", text or "")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"(\w)-\n(\w)", r"\1\2", normalized)

    raw_lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in normalized.splitlines()]
    cleaned_lines = [ln for ln in raw_lines if ln and not _FOOTER_RE.match(ln)]
    if not cleaned_lines:
        return ""

    blocks: list[str] = []
    current_lines: list[str] = []

    for line in cleaned_lines:
        is_heading = _is_heading_line(line)
        is_list_item = bool(re.match(r"^(?:•|[a-d]\.|\d+\s+\.)", line))

        if is_heading:
            if current_lines:
                blocks.append(" ".join(current_lines))
                current_lines = []
            blocks.append(line)
        elif is_list_item:
            if current_lines:
                blocks.append(" ".join(current_lines))
                current_lines = []
            current_lines.append(line)
        else:
            if current_lines and current_lines[-1].endswith((".", "!", "?")) and len(current_lines[-1]) > 45:
                blocks.append(" ".join(current_lines))
                current_lines = [line]
            else:
                current_lines.append(line)

    if current_lines:
        blocks.append(" ".join(current_lines))

    return "\n\n".join(blocks).strip()


def classify_page(norm_text: str) -> tuple[bool, str | None]:
    """Classify whether a normalized PDF page is valid content or excluded front-matter."""
    if not norm_text:
        return False, "blank_page"
    upper = norm_text.upper()
    if upper.startswith("CONTENTS"):
        return False, "table_of_contents"
    if len(norm_text) < 250:
        if "SENIOR CONTRIBUTING AUTHORS" in upper or "INTRODUCTION TO" in upper:
            return False, "cover_or_title_page"
        return False, "too_short_under_250_chars"
    return True, None


def load_pdf(
    path: Path,
    document_id: str,
    source: str,
    extra_metadata: dict[str, Any] | None = None,
    ingestion_log: IngestionResult | None = None,
) -> list[DocumentPage]:
    """Extract each physical PDF page, normalize text, and filter non-content pages."""
    pages: list[DocumentPage] = []
    base_meta = dict(extra_metadata or {})
    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        if ingestion_log is not None:
            ingestion_log.errors.append(
                {"document_id": document_id, "source": source, "error": str(exc)}
            )
        raise

    for page_num, pdf_page in enumerate(reader.pages, start=1):
        try:
            raw = pdf_page.extract_text() or ""
        except Exception as exc:
            if ingestion_log is not None:
                ingestion_log.errors.append(
                    {"document_id": document_id, "source": source, "page": page_num, "error": str(exc)}
                )
            continue

        norm = normalize_text(raw)
        is_valid, reason = classify_page(norm)
        if not is_valid:
            if ingestion_log is not None:
                ingestion_log.excluded_pages.append(
                    {
                        "document_id": document_id,
                        "source": source,
                        "page": page_num,
                        "reason": reason,
                        "char_count": len(norm),
                    }
                )
            continue

        meta = {
            **base_meta,
            "char_count": len(norm),
        }
        doc_page = DocumentPage(
            document_id=document_id,
            source=source,
            page=page_num,
            text=norm,
            metadata=meta,
        )
        pages.append(doc_page)
        if ingestion_log is not None:
            ingestion_log.pages.append(doc_page)

    return pages
