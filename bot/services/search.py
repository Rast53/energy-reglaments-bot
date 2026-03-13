from __future__ import annotations

import logging
from typing import Any

import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
)

logger = logging.getLogger(__name__)

OPENROUTER_EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"


async def embed_text(
    text: str,
    api_key: str,
    model: str = "intfloat/multilingual-e5-large",
) -> list[float]:
    """Embed a single text via OpenRouter embeddings API (httpx, no openai SDK)."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            OPENROUTER_EMBEDDINGS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "input": [text]},
        )
        resp.raise_for_status()
        data = resp.json()
        vector: list[float] = data["data"][0]["embedding"]
        logger.debug("Embedded query text, dim=%d", len(vector))
        return vector


def _build_filter(mode: str) -> Filter | None:
    """Build Qdrant filter based on query mode."""
    if mode == "current":
        return Filter(
            must=[FieldCondition(key="is_current", match=MatchValue(value=True))]
        )
    if mode == "future":
        return Filter(
            must=[FieldCondition(key="status", match=MatchValue(value="future"))]
        )
    if mode == "both":
        return Filter(
            must=[
                FieldCondition(
                    key="status", match=MatchAny(any=["current", "future"])
                )
            ]
        )
    return None


async def search_qdrant(
    vector: list[float],
    mode: str,
    client: AsyncQdrantClient,
    collection: str,
    limit: int = 5,
) -> list[Any]:
    """Search Qdrant for similar chunks with mode-based filtering."""
    query_filter = _build_filter(mode)
    results = await client.query_points(
        collection_name=collection,
        query=vector,
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
    )
    logger.info(
        "Qdrant search: mode=%s, results=%d",
        mode,
        len(results.points),
    )
    return list(results.points)
