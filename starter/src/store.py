"""Persistent vector stores with Cosine similarity search and metadata filtering."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import psycopg
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
    VectorParams,
)

from .models import Chunk

PERMITTED_FILTER_KEYS = frozenset(
    {"section", "chapter", "year", "document_type", "category", "language"}
)


def _validate_vectors(chunks: list[Chunk], vectors: list[list[float]], dimensions: int) -> None:
    if len(chunks) != len(vectors):
        raise ValueError(f"Chunk/vector count mismatch: {len(chunks)} vs {len(vectors)}")
    for idx, vec in enumerate(vectors):
        if len(vec) != dimensions:
            raise ValueError(
                f"Vector {idx} dimension mismatch: expected {dimensions}, got {len(vec)}"
            )


def _validate_filters(filters: dict[str, Any] | None) -> dict[str, Any]:
    if not filters:
        return {}
    clean: dict[str, Any] = {}
    for key, val in filters.items():
        if key not in PERMITTED_FILTER_KEYS:
            raise ValueError(f"Unsupported metadata filter key: {key}")
        clean[key] = val
    return clean


class PgVectorStore:
    """PostgreSQL + pgvector persistent store (used when Docker/PostgreSQL is running)."""

    def __init__(self, database_url: str, dimensions: int) -> None:
        if not database_url:
            raise ValueError("database_url must not be empty")
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.database_url = database_url
        self.dimensions = dimensions
        self.backend_name = "postgresql+pgvector"

    def create_schema(self) -> None:
        ddl = f"""
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE TABLE IF NOT EXISTS rag_chunks (
            strategy TEXT NOT NULL,
            chunk_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            source TEXT NOT NULL,
            page INTEGER NOT NULL,
            section TEXT,
            chapter TEXT,
            year INTEGER,
            text TEXT NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
            embedding vector({self.dimensions}) NOT NULL,
            PRIMARY KEY (strategy, chunk_id)
        );
        CREATE INDEX IF NOT EXISTS idx_rag_chunks_strategy_section
            ON rag_chunks (strategy, section);
        """
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
            conn.commit()

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if not chunks:
            return
        _validate_vectors(chunks, vectors, self.dimensions)
        doc_ids = sorted({c.document_id for c in chunks})
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                # Remove obsolete chunks for any re-ingested document before writing
                cur.execute(
                    "DELETE FROM rag_chunks WHERE strategy = %s AND document_id = ANY(%s)",
                    (strategy, doc_ids),
                )
                sql = """
                INSERT INTO rag_chunks
                    (strategy, chunk_id, document_id, source, page, section, chapter, year, text, metadata, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::vector)
                ON CONFLICT (strategy, chunk_id) DO UPDATE SET
                    document_id = EXCLUDED.document_id,
                    source = EXCLUDED.source,
                    page = EXCLUDED.page,
                    section = EXCLUDED.section,
                    chapter = EXCLUDED.chapter,
                    year = EXCLUDED.year,
                    text = EXCLUDED.text,
                    metadata = EXCLUDED.metadata,
                    embedding = EXCLUDED.embedding
                """
                rows = [
                    (
                        strategy,
                        c.chunk_id,
                        c.document_id,
                        c.source,
                        c.page,
                        c.metadata.get("section"),
                        c.metadata.get("chapter"),
                        c.metadata.get("year"),
                        c.text,
                        json.dumps(c.metadata, ensure_ascii=False),
                        "[" + ",".join(f"{x:.8f}" for x in v) + "]",
                    )
                    for c, v in zip(chunks, vectors)
                ]
                cur.executemany(sql, rows)
            conn.commit()

    def count_chunks(self, strategy: str | None = None) -> int:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                if strategy is None:
                    cur.execute("SELECT COUNT(*) FROM rag_chunks")
                else:
                    cur.execute("SELECT COUNT(*) FROM rag_chunks WHERE strategy = %s", (strategy,))
                row = cur.fetchone()
                return int(row[0]) if row else 0

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if len(query_vector) != self.dimensions:
            raise ValueError(
                f"Query vector dimension mismatch: expected {self.dimensions}, got {len(query_vector)}"
            )
        clean_filters = _validate_filters(filters)
        vec_lit = "[" + ",".join(f"{x:.8f}" for x in query_vector) + "]"
        clauses = ["strategy = %s"]
        params: list[Any] = [vec_lit, strategy]
        for key, val in clean_filters.items():
            if key in {"section", "chapter"}:
                clauses.append(f"{key} = %s")
                params.append(val)
            elif key == "year":
                clauses.append("year = %s")
                params.append(int(val))
            else:
                clauses.append("metadata ->> %s = %s")
                params.extend([key, str(val)])
        params.extend([vec_lit, top_k])
        where_sql = " AND ".join(clauses)
        sql = f"""
        SELECT chunk_id, document_id, source, page, text, metadata,
               1 - (embedding <=> %s::vector) AS cosine_score
        FROM rag_chunks
        WHERE {where_sql}
        ORDER BY embedding <=> %s::vector ASC
        LIMIT %s
        """
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        return [
            {
                "chunk_id": r[0],
                "document_id": r[1],
                "source": r[2],
                "page": int(r[3]),
                "text": r[4],
                "metadata": r[5] if isinstance(r[5], dict) else json.loads(r[5]),
                "score": float(r[6]),
            }
            for r in rows
        ]


class QdrantVectorStore:
    """Persistent local Qdrant vector store using Cosine distance and exact search."""

    def __init__(
        self,
        storage_path: Path | str,
        dimensions: int,
        collection_name: str = "day6_chunks",
    ) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.dimensions = dimensions
        self.collection_name = collection_name
        self.backend_name = "qdrant-local"
        self.client = QdrantClient(path=str(self.storage_path))

    def create_schema(self) -> None:
        existing = {c.name for c in self.client.get_collections().collections}
        if self.collection_name not in existing:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.dimensions, distance=Distance.COSINE),
            )

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if not chunks:
            return
        _validate_vectors(chunks, vectors, self.dimensions)
        doc_ids = sorted({c.document_id for c in chunks})
        for doc_id in doc_ids:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=FilterSelector(
                    filter=Filter(
                        must=[
                            FieldCondition(key="strategy", match=MatchValue(value=strategy)),
                            FieldCondition(key="document_id", match=MatchValue(value=doc_id)),
                        ]
                    )
                ),
            )

        points: list[PointStruct] = []
        for chunk, vec in zip(chunks, vectors):
            point_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{strategy}:{chunk.chunk_id}"))
            payload = {
                "strategy": strategy,
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "source": chunk.source,
                "page": chunk.page,
                "text": chunk.text,
                **chunk.metadata,
            }
            points.append(PointStruct(id=point_uuid, vector=vec, payload=payload))

        self.client.upsert(collection_name=self.collection_name, points=points)

    def count_chunks(self, strategy: str | None = None) -> int:
        count_filter = None
        if strategy is not None:
            count_filter = Filter(
                must=[FieldCondition(key="strategy", match=MatchValue(value=strategy))]
            )
        res = self.client.count(
            collection_name=self.collection_name,
            count_filter=count_filter,
            exact=True,
        )
        return int(res.count)

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if len(query_vector) != self.dimensions:
            raise ValueError(
                f"Query vector dimension mismatch: expected {self.dimensions}, got {len(query_vector)}"
            )
        clean_filters = _validate_filters(filters)
        conditions = [FieldCondition(key="strategy", match=MatchValue(value=strategy))]
        for key, val in clean_filters.items():
            conditions.append(FieldCondition(key=key, match=MatchValue(value=val)))

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=Filter(must=conditions),
            limit=top_k,
            with_payload=True,
        )

        hits: list[dict[str, Any]] = []
        for pt in response.points:
            payload = dict(pt.payload or {})
            chunk_id = payload.pop("chunk_id", str(pt.id))
            document_id = payload.pop("document_id", "")
            source = payload.pop("source", "")
            page = int(payload.pop("page", 0))
            text = payload.pop("text", "")
            payload.pop("strategy", None)
            hits.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "source": source,
                    "page": page,
                    "text": text,
                    "score": float(pt.score),
                    "metadata": payload,
                }
            )
        return hits

    def close(self) -> None:
        self.client.close()
