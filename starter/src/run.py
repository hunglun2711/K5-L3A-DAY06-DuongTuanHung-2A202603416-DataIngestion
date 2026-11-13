"""End-to-end Day 06 Data Ingestion & Benchmark Pipeline."""
from __future__ import annotations

import json
import os
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .chunking import by_paragraph, fixed_size
from .embeddings import MyEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import IngestionResult, load_pdf
from .models import Chunk, DocumentPage
from .store import PgVectorStore, QdrantVectorStore


def _chunk_length_stats(chunks: list[Chunk]) -> dict[str, Any]:
    lengths = [len(c.text) for c in chunks]
    return {
        "chunk_count": len(chunks),
        "total_chars": sum(lengths),
        "min_chars": min(lengths) if lengths else 0,
        "median_chars": float(statistics.median(lengths)) if lengths else 0.0,
        "mean_chars": round(statistics.mean(lengths), 2) if lengths else 0.0,
        "max_chars": max(lengths) if lengths else 0,
    }


def _build_chunks(pages: list[DocumentPage], strategy: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        if strategy == "A":
            chunks.extend(fixed_size(page, size=500, overlap=50))
        elif strategy in {"B", "C"}:
            chunks.extend(by_paragraph(page, max_size=800))
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    return chunks


def main() -> None:
    starter_dir = Path(__file__).resolve().parents[1]
    repo_root = starter_dir.parent
    load_dotenv(starter_dir / ".env")

    manifest_path = repo_root / "data" / "manifest.json"
    benchmark_path = repo_root / "benchmark" / "questions.json"
    results_dir = repo_root / "results"
    starter_results_dir = starter_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    starter_results_dir.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_lookup = {doc["source_id"]: doc for doc in manifest["documents"]}
    questions = json.loads(benchmark_path.read_text(encoding="utf-8"))

    # 1. Load & normalize corpus
    ingestion_log = IngestionResult()
    for doc in manifest["documents"]:
        pdf_path = repo_root / doc["source_path_or_url"]
        load_pdf(
            path=pdf_path,
            document_id=doc["source_id"],
            source=doc["source_path_or_url"],
            extra_metadata={
                "section": doc["section"],
                "chapter": doc["chapter"],
                "year": doc["year"],
                "license": doc["license_or_permission"],
            },
            ingestion_log=ingestion_log,
        )

    valid_page_count = len(ingestion_log.pages)
    if valid_page_count < 30:
        raise RuntimeError(
            f"Corpus has only {valid_page_count} valid content pages (< 30 required)."
        )

    ingestion_report = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "corpus_name": manifest["corpus_name"],
        "valid_content_pages": valid_page_count,
        "excluded_pages_count": len(ingestion_log.excluded_pages),
        "excluded_pages": ingestion_log.excluded_pages,
        "errors_count": len(ingestion_log.errors),
        "errors": ingestion_log.errors,
        "total_normalized_chars": sum(len(p.text) for p in ingestion_log.pages),
    }
    (results_dir / "ingestion_log.json").write_text(
        json.dumps(ingestion_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"[Ingestion] Valid pages={valid_page_count}, Excluded={len(ingestion_log.excluded_pages)}, "
        f"Errors={len(ingestion_log.errors)}, Chars={ingestion_report['total_normalized_chars']}"
    )

    # 2. Initialize real embedder & persistent vector store
    embedder = MyEmbedder(
        cache_path=starter_results_dir / ".embedding_cache.json",
        env_path=starter_dir / ".env",
    )

    use_pgvector = os.getenv("USE_PGVECTOR", "").strip() == "1"
    if use_pgvector:
        db_url = os.getenv("DATABASE_URL", "")
        store: Any = PgVectorStore(database_url=db_url, dimensions=embedder.dimensions)
        fallback_reason = None
    else:
        store = QdrantVectorStore(
            storage_path=starter_dir / "qdrant_storage",
            dimensions=embedder.dimensions,
            collection_name="day6_chunks",
        )
        fallback_reason = (
            "Docker Desktop Linux engine failed with Wsl/WSL_E_WSL_OPTIONAL_COMPONENT_REQUIRED "
            "(500 Internal Server Error on dockerDesktopLinuxEngine pipe because Windows WSL optional "
            "component is not enabled). Switched to persistent local QdrantVectorStore per GUIDE.md/RULES.md."
        )

    store.create_schema()

    env_log = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "os": platform.platform(),
        "embedding_provider": "OpenRouter",
        "embedding_model": embedder.model_name,
        "embedding_dimensions": embedder.dimensions,
        "vector_store_backend": store.backend_name,
        "distance_metric": "Cosine",
        "search_mode": "exact",
        "storage_location": str(starter_dir / "qdrant_storage") if not use_pgvector else "postgresql:55433/day6_lab",
        "docker_pgvector_fallback_reason": fallback_reason,
    }
    (results_dir / "environment_log.json").write_text(
        json.dumps(env_log, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 3. Build, embed, and ingest strategies A, B, C
    strategies_cfg = {
        "A": {"chunking": "fixed_size", "size": 500, "overlap": 50, "use_metadata_filter": False},
        "B": {"chunking": "by_paragraph", "max_size": 800, "overlap": 0, "use_metadata_filter": False},
        "C": {"chunking": "by_paragraph", "max_size": 800, "overlap": 0, "use_metadata_filter": True},
    }

    strategy_stats: dict[str, dict[str, Any]] = {}
    strategy_chunks: dict[str, list[Chunk]] = {}
    strategy_vectors: dict[str, list[list[float]]] = {}

    for strat in ("A", "B", "C"):
        t0 = time.perf_counter()
        calls_before = embedder.api_calls
        tokens_before = embedder.billed_tokens
        cost_before = embedder.billed_cost_usd
        hits_before = embedder.cache_hits

        chunks = _build_chunks(ingestion_log.pages, strat)
        vectors = embedder.embed_documents([c.text for c in chunks])
        store.upsert(strat, chunks, vectors)
        elapsed = round(time.perf_counter() - t0, 3)

        strategy_chunks[strat] = chunks
        strategy_vectors[strat] = vectors
        intrinsic_tokens, intrinsic_cost = embedder.estimate_texts_footprint(
            [c.text for c in chunks]
        )
        stats = {
            **strategies_cfg[strat],
            **_chunk_length_stats(chunks),
            "stored_count": store.count_chunks(strat),
            "ingest_time_sec": elapsed,
            "api_calls": embedder.api_calls - calls_before,
            "cache_hits": embedder.cache_hits - hits_before,
            "billed_tokens": embedder.billed_tokens - tokens_before,
            "billed_cost_usd": round(embedder.billed_cost_usd - cost_before, 8),
            "intrinsic_tokens": intrinsic_tokens,
            "intrinsic_cost_usd": intrinsic_cost,
        }
        strategy_stats[strat] = stats
        print(
            f"[Ingest {strat}] chunks={stats['chunk_count']} stored={stats['stored_count']} "
            f"time={elapsed}s tokens={stats['billed_tokens']} cost=${stats['billed_cost_usd']}"
        )

    # 4. Idempotent re-ingestion check on Strategy A
    count_before_reingest = store.count_chunks("A")
    store.upsert("A", strategy_chunks["A"], strategy_vectors["A"])
    count_after_reingest = store.count_chunks("A")
    reingest_check = {
        "strategy_tested": "A",
        "count_before_reingest": count_before_reingest,
        "count_after_reingest": count_after_reingest,
        "no_duplicates": count_before_reingest == count_after_reingest,
    }
    (results_dir / "reingest_check.json").write_text(
        json.dumps(reingest_check, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[Re-ingest Check] Strategy A: before={count_before_reingest}, after={count_after_reingest}")

    # 5. Embed benchmark queries once and run top-3 retrieval across A, B, C
    q_tokens_before = embedder.billed_tokens
    q_cost_before = embedder.billed_cost_usd
    query_vectors = {q["id"]: embedder.embed_query(q["question"]) for q in questions}
    query_embed_usage = {
        "total_queries": len(questions),
        "billed_tokens": embedder.billed_tokens - q_tokens_before,
        "billed_cost_usd": round(embedder.billed_cost_usd - q_cost_before, 8),
    }

    all_traces: list[dict[str, Any]] = []
    for strat in ("A", "B", "C"):
        strat_traces: list[dict[str, Any]] = []
        for q in questions:
            applied_filters = q.get("filter") if strat == "C" else None
            hits = store.search(
                strategy=strat,
                query_vector=query_vectors[q["id"]],
                top_k=3,
                filters=applied_filters,
            )
            trace = evaluate_query(
                question=q,
                hits=hits,
                strategy=strat,
                applied_filters=applied_filters,
                manifest_lookup=manifest_lookup,
            )
            strat_traces.append(trace)
            all_traces.append(trace)

        (results_dir / f"traces_{strat}.json").write_text(
            json.dumps(strat_traces, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    retrieval_summary = summarize(all_traces)
    full_summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": env_log,
        "strategy_stats": strategy_stats,
        "query_embedding_usage": query_embed_usage,
        "total_embedding_usage": embedder.get_usage_summary(),
        "reingest_check": reingest_check,
        "retrieval_metrics": retrieval_summary,
    }
    (results_dir / "metrics_summary.json").write_text(
        json.dumps(full_summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 6. Export first 10 sorted (document_id, page) positions & covering chunks for Coherence audit
    sorted_positions = sorted({(p.document_id, p.page) for p in ingestion_log.pages})[:10]
    coherence_samples = []
    for doc_id, page_num in sorted_positions:
        entry: dict[str, Any] = {"document_id": doc_id, "page": page_num, "chunks_by_strategy": {}}
        for strat in ("A", "B", "C"):
            matched = [
                {"chunk_id": c.chunk_id, "char_count": len(c.text), "text": c.text}
                for c in strategy_chunks[strat]
                if c.document_id == doc_id and c.page == page_num
            ]
            entry["chunks_by_strategy"][strat] = matched
        coherence_samples.append(entry)
    (results_dir / "coherence_positions.json").write_text(
        json.dumps(coherence_samples, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    if hasattr(store, "close"):
        store.close()

    print("\n=== Retrieval Summary ===")
    for strat in ("A", "B", "C"):
        for split in ("dev", "test"):
            m = retrieval_summary[strat][split]
            print(
                f"Strategy {strat} [{split:4s}]: Hit@1={m['hit_at_1_str']} ({m['hit_at_1_rate']:.1%}) | "
                f"Evidence Hit@3={m['evidence_hit_at_3_str']} ({m['evidence_hit_at_3_rate']:.1%}) | "
                f"Meta={m['metadata_valid_str']} | Filter={m['filter_compliant_str']}"
            )


if __name__ == "__main__":
    main()
