"""Download OpenStax Introduction to Python Programming (CC BY 4.0), slice 4 chapters, and write data/manifest.json."""
from __future__ import annotations

import json
import re
import tempfile
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader, PdfWriter

OPENSTAX_PDF_URL = (
    "https://assets.openstax.org/oscms-prodcms/media/documents/"
    "Introduction_to_Python_Programming-WEB.pdf"
)
LICENSE = "Creative Commons Attribution 4.0 International (CC BY 4.0)"

CHAPTER_SPECS = [
    {
        "source_id": "openstax-py-ch01",
        "filename": "openstax_python_ch01_intro.pdf",
        "title": "Introduction to Python Programming — Chapter 1 Excerpt (Statements, Input/Output, Variables)",
        "section": "ch01_statements_variables",
        "chapter": "Chapter 1: Statements",
        "year": 2024,
        "book_indices": [0, 2, 6] + list(range(16, 26)),
    },
    {
        "source_id": "openstax-py-ch03",
        "filename": "openstax_python_ch03_types.pdf",
        "title": "Introduction to Python Programming — Chapter 3 Excerpt (Strings, f-Strings, Objects)",
        "section": "ch03_data_types",
        "chapter": "Chapter 3: Objects",
        "year": 2024,
        "book_indices": list(range(76, 87)),
    },
    {
        "source_id": "openstax-py-ch04",
        "filename": "openstax_python_ch04_branching.pdf",
        "title": "Introduction to Python Programming — Chapter 4 Excerpt (Booleans, If-Else, Boolean Operations)",
        "section": "ch04_branching",
        "chapter": "Chapter 4: Decisions",
        "year": 2024,
        "book_indices": list(range(94, 104)),
    },
    {
        "source_id": "openstax-py-ch05",
        "filename": "openstax_python_ch05_loops.pdf",
        "title": "Introduction to Python Programming — Chapter 5 Excerpt (While Loops, For Loops, Nested Loops)",
        "section": "ch05_loops",
        "chapter": "Chapter 5: Loops",
        "year": 2024,
        "book_indices": list(range(124, 134)),
    },
]


def normalize_text(text: str) -> str:
    """Normalize Unicode and whitespace while keeping paragraph breaks."""
    text = unicodedata.normalize("NFC", text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    joined = "\n".join(lines)
    joined = re.sub(r"\n{3,}", "\n\n", joined)
    return joined.strip()


def classify_page(norm_text: str) -> tuple[bool, str | None]:
    """Return (is_valid_content, exclusion_reason)."""
    if not norm_text:
        return False, "blank_page"
    upper = norm_text.upper()
    if upper.startswith("CONTENTS\n") or "\nCONTENTS\n" in upper[:120]:
        return False, "table_of_contents"
    if len(norm_text) < 250:
        if "SENIOR CONTRIBUTING AUTHORS" in upper or "INTRODUCTION TO" in upper:
            return False, "cover_or_title_page"
        return False, "too_short_under_250_chars"
    return True, None


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    data_dir = repo_root / "starter" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = repo_root / "data" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_pdf = Path(tempfile.gettempdir()) / "openstax_python_prog.pdf"
    if not tmp_pdf.exists() or tmp_pdf.stat().st_size < 1_000_000:
        req = urllib.request.Request(OPENSTAX_PDF_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            tmp_pdf.write_bytes(resp.read())

    reader = PdfReader(str(tmp_pdf))
    accessed_at = datetime.now(timezone.utc).isoformat()

    documents_manifest = []
    total_physical = 0
    total_valid = 0
    total_chars = 0

    for spec in CHAPTER_SPECS:
        writer = PdfWriter()
        for book_idx in spec["book_indices"]:
            writer.add_page(reader.pages[book_idx])
        out_pdf = data_dir / spec["filename"]
        with out_pdf.open("wb") as f:
            writer.write(f)

        # Re-read the written excerpt PDF to ensure page numbers & char counts match 1:1
        sub_reader = PdfReader(str(out_pdf))
        valid_pages = []
        excluded_pages = []
        doc_chars = 0

        for page_num, page in enumerate(sub_reader.pages, start=1):
            norm = normalize_text(page.extract_text() or "")
            is_valid, reason = classify_page(norm)
            if is_valid:
                valid_pages.append(page_num)
                doc_chars += len(norm)
            else:
                excluded_pages.append({"page": page_num, "reason": reason, "char_count": len(norm)})

        total_physical += len(sub_reader.pages)
        total_valid += len(valid_pages)
        total_chars += doc_chars

        documents_manifest.append(
            {
                "source_id": spec["source_id"],
                "title": spec["title"],
                "source_path_or_url": f"starter/data/{spec['filename']}",
                "upstream_url": OPENSTAX_PDF_URL,
                "license_or_permission": LICENSE,
                "accessed_at": accessed_at,
                "section": spec["section"],
                "chapter": spec["chapter"],
                "year": spec["year"],
                "source_book_page_indices_0based": spec["book_indices"],
                "physical_page_count": len(sub_reader.pages),
                "valid_page_numbers": valid_pages,
                "excluded_pages": excluded_pages,
                "valid_page_count": len(valid_pages),
                "total_normalized_chars": doc_chars,
            }
        )

    manifest = {
        "corpus_name": "OpenStax Introduction to Python Programming (4-Chapter Excerpt)",
        "publisher": "OpenStax, Rice University",
        "source_url": OPENSTAX_PDF_URL,
        "license_or_permission": LICENSE,
        "accessed_at": accessed_at,
        "version_note": "WEB PDF edition retrieved from OpenStax CMS assets",
        "page_counting_rule": (
            "Each physical PDF page is extracted via pypdf and normalized (NFC, whitespace cleanup). "
            "Pages that are blank (0 chars), Table of Contents ('CONTENTS'), or cover/title pages "
            "under 250 normalized characters are excluded from valid content pages and logged."
        ),
        "total_physical_pages": total_physical,
        "total_valid_content_pages": total_valid,
        "total_excluded_pages": total_physical - total_valid,
        "total_normalized_chars": total_chars,
        "documents": documents_manifest,
    }

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote manifest: {manifest_path}")
    print(f"Physical pages: {total_physical} | Valid content pages: {total_valid} | Total chars: {total_chars}")

    # Remove large temporary download
    if tmp_pdf.exists():
        tmp_pdf.unlink()
        print(f"Removed temporary full PDF: {tmp_pdf}")


if __name__ == "__main__":
    main()
