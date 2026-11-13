"""Verify every benchmark question's evidence_quote exists verbatim in the normalized gold page."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from starter.src.ingestion import load_pdf


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    manifest = json.loads((repo_root / "data" / "manifest.json").read_text(encoding="utf-8"))
    page_map: dict[tuple[str, int], str] = {}
    for doc in manifest["documents"]:
        pdf_path = repo_root / doc["source_path_or_url"]
        for page in load_pdf(pdf_path, doc["source_id"], doc["source_path_or_url"]):
            page_map[(page.document_id, page.page)] = re.sub(r"\s+", " ", page.text).strip()

    questions = json.loads((repo_root / "benchmark" / "questions.json").read_text(encoding="utf-8"))
    results = []
    all_ok = True
    for q in questions:
        key = (q["gold_source_id"], q["gold_page"])
        norm_page = page_map.get(key, "")
        norm_quote = re.sub(r"\s+", " ", q["evidence_quote"]).strip()
        matched = bool(norm_page and norm_quote in norm_page)
        if not matched:
            all_ok = False
        results.append(
            {
                "id": q["id"],
                "split": q["split"],
                "type": q["type"],
                "gold_source_id": q["gold_source_id"],
                "gold_page": q["gold_page"],
                "filter": q.get("filter"),
                "verified_in_normalized_page": matched,
            }
        )
        print(f"{q['id']} ({q['split']}, {q['type']}): match={matched} | {key}")

    report = {
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "total_questions": len(questions),
        "dev_count": sum(1 for q in questions if q["split"] == "dev"),
        "test_count": sum(1 for q in questions if q["split"] == "test"),
        "filter_count": sum(1 for q in questions if q.get("filter")),
        "test_filter_count": sum(1 for q in questions if q["split"] == "test" and q.get("filter")),
        "all_evidence_verified": all_ok,
        "checks": results,
    }
    out_path = repo_root / "benchmark" / "verification_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"All verified: {all_ok} -> {out_path}")
    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

