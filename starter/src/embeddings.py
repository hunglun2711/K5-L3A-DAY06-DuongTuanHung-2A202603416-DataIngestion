"""Real embedding provider using OpenRouter Embeddings API with persistent disk caching."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Protocol

import httpx
from dotenv import load_dotenv

OPENROUTER_EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"
DEFAULT_MODEL = "openai/text-embedding-3-small"
MODEL_DIMENSIONS = {
    "openai/text-embedding-3-small": 1536,
    "openai/text-embedding-3-large": 3072,
    "text-embedding-3-small": 1536,
}


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """OpenRouter embedding adapter; fails loudly on missing key or API errors."""

    def __init__(
        self,
        model_name: str | None = None,
        cache_path: Path | None = None,
        env_path: Path | None = None,
    ) -> None:
        if env_path is None:
            env_path = Path(__file__).resolve().parents[1] / ".env"
        load_dotenv(env_path)

        self.model_name = (model_name or os.getenv("EMBEDDING_MODEL") or DEFAULT_MODEL).strip()
        self.api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not self.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is missing in starter/.env. "
                "Real embeddings are required; mock fallback is disabled."
            )
        if self.model_name not in MODEL_DIMENSIONS:
            raise ValueError(f"Unsupported embedding model '{self.model_name}'")
        self.dimensions = MODEL_DIMENSIONS[self.model_name]

        if cache_path is None:
            cache_path = Path(__file__).resolve().parents[1] / "results" / ".embedding_cache.json"
        self.cache_path = cache_path
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, dict] = self._load_cache()

        # Accounting counters for the current session
        self.api_calls = 0
        self.billed_tokens = 0
        self.billed_cost_usd = 0.0
        self.cache_hits = 0

    def _load_cache(self) -> dict[str, dict]:
        if not self.cache_path.exists():
            return {}
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_cache(self) -> None:
        self.cache_path.write_text(json.dumps(self._cache), encoding="utf-8")

    def _cache_key(self, text: str) -> str:
        raw = f"{self.model_name}::{text}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _request_batch(self, batch: list[str]) -> tuple[list[list[float]], int, float]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model_name, "input": batch}
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(OPENROUTER_EMBEDDINGS_URL, headers=headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(
                f"OpenRouter embeddings API error {resp.status_code}: {resp.text[:400]}"
            )
        body = resp.json()
        items = sorted(body.get("data", []), key=lambda x: x["index"])
        if len(items) != len(batch):
            raise RuntimeError(
                f"Embedding count mismatch: sent {len(batch)}, got {len(items)}"
            )
        vectors = [item["embedding"] for item in items]
        for vec in vectors:
            if len(vec) != self.dimensions:
                raise RuntimeError(
                    f"Dimension mismatch: expected {self.dimensions}, got {len(vec)}"
                )
        usage = body.get("usage", {})
        tokens = int(usage.get("prompt_tokens") or usage.get("total_tokens") or 0)
        cost = float(usage.get("cost") or 0.0)
        self.api_calls += 1
        self.billed_tokens += tokens
        self.billed_cost_usd += cost
        return vectors, tokens, cost

    def embed_documents(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Embed documents in batches, reusing cached vectors for identical text+model."""
        if not texts:
            return []

        results: list[list[float] | None] = [None] * len(texts)
        missing_indices: list[int] = []
        missing_texts: list[str] = []

        for idx, text in enumerate(texts):
            key = self._cache_key(text)
            entry = self._cache.get(key)
            if entry and len(entry.get("embedding", [])) == self.dimensions:
                results[idx] = entry["embedding"]
                self.cache_hits += 1
            else:
                missing_indices.append(idx)
                missing_texts.append(text)

        for start in range(0, len(missing_texts), batch_size):
            batch_texts = missing_texts[start : start + batch_size]
            batch_idx = missing_indices[start : start + batch_size]
            vectors, tokens, cost = self._request_batch(batch_texts)
            approx_tok_per_item = tokens / max(len(batch_texts), 1)
            approx_cost_per_item = cost / max(len(batch_texts), 1)
            for local_i, vec in enumerate(vectors):
                orig_i = batch_idx[local_i]
                key = self._cache_key(texts[orig_i])
                self._cache[key] = {
                    "embedding": vec,
                    "approx_tokens": approx_tok_per_item,
                    "approx_cost_usd": approx_cost_per_item,
                }
                results[orig_i] = vec
            self._save_cache()

        return [vec for vec in results if vec is not None]

    def embed_query(self, question: str) -> list[float]:
        """Embed a single query string using the exact same model and space."""
        return self.embed_documents([question])[0]

    def estimate_texts_footprint(self, texts: list[str]) -> tuple[int, float]:
        """Sum cached token & USD cost footprint for a list of texts."""
        total_tok = 0.0
        total_cost = 0.0
        for text in texts:
            entry = self._cache.get(self._cache_key(text))
            if entry:
                total_tok += float(entry.get("approx_tokens", 0.0))
                total_cost += float(entry.get("approx_cost_usd", 0.0))
        return round(total_tok), round(total_cost, 8)

    def get_usage_summary(self) -> dict[str, float | int | str]:
        return {
            "provider": "OpenRouter",
            "model_name": self.model_name,
            "dimensions": self.dimensions,
            "api_calls_this_run": self.api_calls,
            "cache_hits_this_run": self.cache_hits,
            "billed_tokens_this_run": self.billed_tokens,
            "billed_cost_usd_this_run": round(self.billed_cost_usd, 8),
        }
