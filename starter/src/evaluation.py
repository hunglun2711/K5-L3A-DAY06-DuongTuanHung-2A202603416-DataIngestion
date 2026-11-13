"""Evaluate retrieved chunks against verified gold evidence and metadata rules."""
from __future__ import annotations

import re
from typing import Any


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _as_set(val: Any) -> set[Any]:
    if isinstance(val, list):
        return set(val)
    return {val}


def evaluate_query(
    question: dict[str, Any],
    hits: list[dict[str, Any]],
    strategy: str,
    applied_filters: dict[str, Any] | None = None,
    manifest_lookup: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Check source/page, exact gold evidence presence, metadata validity, and filter compliance."""
    gold_sources = _as_set(question["gold_source_id"])
    gold_pages = _as_set(question["gold_page"])
    norm_quote = _collapse_ws(question["evidence_quote"])
    quote_tokens = norm_quote.split(" ")

    evaluated_hits: list[dict[str, Any]] = []
    hit_flags: list[bool] = []
    partial_source_page_hits: list[str] = []

    for rank, hit in enumerate(hits[:3], start=1):
        norm_text = _collapse_ws(hit.get("text", ""))
        source_match = hit.get("document_id") in gold_sources
        page_match = hit.get("page") in gold_pages
        full_quote_match = bool(norm_quote and norm_quote in norm_text)
        is_hit = bool(source_match and page_match and full_quote_match)

        # Diagnostic: detect when a chunk is on the right page but evidence was cut by chunk boundary
        partial_split = False
        if source_match and page_match and not full_quote_match and len(quote_tokens) >= 6:
            first_half = " ".join(quote_tokens[: len(quote_tokens) // 2])
            second_half = " ".join(quote_tokens[len(quote_tokens) // 2 :])
            if first_half in norm_text or second_half in norm_text:
                partial_split = True
                partial_source_page_hits.append(hit.get("chunk_id", ""))

        meta = hit.get("metadata") or {}
        meta_complete = bool(
            hit.get("document_id")
            and hit.get("source")
            and hit.get("page", 0) > 0
            and meta.get("section")
        )
        meta_matches_manifest = True
        if manifest_lookup and hit.get("document_id") in manifest_lookup:
            doc_m = manifest_lookup[hit["document_id"]]
            meta_matches_manifest = (
                hit.get("source") == doc_m["source_path_or_url"]
                and meta.get("section") == doc_m["section"]
                and hit.get("page") in doc_m["valid_page_numbers"]
            )

        hit_flags.append(is_hit)
        evaluated_hits.append(
            {
                "rank": rank,
                "chunk_id": hit.get("chunk_id"),
                "document_id": hit.get("document_id"),
                "source": hit.get("source"),
                "page": hit.get("page"),
                "score": round(float(hit.get("score", 0.0)), 6),
                "metadata": meta,
                "text": hit.get("text", ""),
                "source_page_match": source_match and page_match,
                "full_evidence_match": full_quote_match,
                "partial_split_evidence": partial_split,
                "is_hit": is_hit,
                "metadata_valid": bool(meta_complete and meta_matches_manifest),
            }
        )

    # Diagnostic multi-chunk union check on gold source/page
    gold_texts_combined = " ".join(
        _collapse_ws(h.get("text", ""))
        for h in hits[:3]
        if h.get("document_id") in gold_sources and h.get("page") in gold_pages
    )
    multi_chunk_union_hit = bool(norm_quote and norm_quote in gold_texts_combined)

    hit_at_1 = bool(hit_flags[0]) if hit_flags else False
    evidence_hit_at_3 = any(hit_flags)

    # Filter compliance check
    query_filter = question.get("filter")
    filter_compliant: bool | None = None
    if applied_filters:
        filter_compliant = bool(hits[:3]) and all(
            all(h.get("metadata", {}).get(k) == v for k, v in applied_filters.items())
            for h in hits[:3]
        )

    return {
        "strategy": strategy,
        "id": question["id"],
        "split": question["split"],
        "type": question["type"],
        "question": question["question"],
        "expected_answer": question["expected_answer"],
        "gold_source_id": question["gold_source_id"],
        "gold_page": question["gold_page"],
        "evidence_quote": question["evidence_quote"],
        "query_filter": query_filter,
        "applied_filters": applied_filters,
        "hit_at_1": hit_at_1,
        "evidence_hit_at_3": evidence_hit_at_3,
        "multi_chunk_union_hit": multi_chunk_union_hit,
        "split_evidence_warning": bool(not evidence_hit_at_3 and partial_source_page_hits),
        "filter_compliant": filter_compliant,
        "hits": evaluated_hits,
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1, Evidence Hit@3, metadata validity, and filter compliance by strategy & split."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for tr in traces:
        groups.setdefault((tr["strategy"], tr["split"]), []).append(tr)

    summary: dict[str, Any] = {}
    for (strategy, split), items in sorted(groups.items()):
        n = len(items)
        h1 = sum(1 for x in items if x["hit_at_1"])
        h3 = sum(1 for x in items if x["evidence_hit_at_3"])
        union_h3 = sum(1 for x in items if x["multi_chunk_union_hit"])
        split_warns = sum(1 for x in items if x["split_evidence_warning"])

        all_hits = [h for x in items for h in x["hits"]]
        meta_ok = sum(1 for h in all_hits if h["metadata_valid"])
        meta_total = len(all_hits)

        filtered_items = [x for x in items if x["applied_filters"]]
        if filtered_items:
            f_ok = sum(1 for x in filtered_items if x["filter_compliant"])
            f_total = len(filtered_items)
            filter_str = f"{f_ok}/{f_total}"
        else:
            f_ok = 0
            f_total = 0
            filter_str = "N/A"

        summary.setdefault(strategy, {})[split] = {
            "total_queries": n,
            "hit_at_1_count": h1,
            "hit_at_1_rate": round(h1 / n, 4) if n else 0.0,
            "hit_at_1_str": f"{h1}/{n}",
            "evidence_hit_at_3_count": h3,
            "evidence_hit_at_3_rate": round(h3 / n, 4) if n else 0.0,
            "evidence_hit_at_3_str": f"{h3}/{n}",
            "multi_chunk_union_hit_at_3": f"{union_h3}/{n}",
            "split_evidence_warnings": split_warns,
            "metadata_valid_count": meta_ok,
            "metadata_checked_total": meta_total,
            "metadata_valid_str": f"{meta_ok}/{meta_total}",
            "filter_compliant_count": f_ok,
            "filter_applied_total": f_total,
            "filter_compliant_str": filter_str,
        }
    return summary
