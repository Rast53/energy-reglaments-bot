from __future__ import annotations

import logging
import time

import httpx

from indexer.models import Chunk

logger = logging.getLogger(__name__)

BATCH_SIZE = 5
RETRY_ATTEMPTS = 3
RETRY_DELAY_SEC = 5

OPENROUTER_EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"


def embed_chunks(
    chunks: list[Chunk],
    api_key: str,
    model: str = "intfloat/multilingual-e5-large",
) -> list[list[float]]:
    """Embed chunk texts in batches via OpenRouter. Returns vectors in input order."""
    all_vectors: list[list[float]] = []

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        texts = [c.text for c in batch]

        vectors = _embed_with_retry(api_key, model, texts, batch_num=i // BATCH_SIZE + 1)
        all_vectors.extend(vectors)

    logger.info("Embedded %d chunks total", len(all_vectors))
    return all_vectors


def _embed_with_retry(
    api_key: str,
    model: str,
    texts: list[str],
    batch_num: int,
) -> list[list[float]]:
    """Call embeddings API with retries on failure."""
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            resp = httpx.post(
                OPENROUTER_EMBEDDINGS_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": model, "input": texts},
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            sorted_items = sorted(data["data"], key=lambda d: d["index"])
            vectors = [d["embedding"] for d in sorted_items]
            logger.info(
                "Batch %d: embedded %d texts (attempt %d)",
                batch_num, len(texts), attempt,
            )
            return vectors
        except Exception:
            if attempt == RETRY_ATTEMPTS:
                logger.exception(
                    "Batch %d: failed after %d attempts", batch_num, RETRY_ATTEMPTS,
                )
                raise
            logger.warning(
                "Batch %d: attempt %d failed, retrying in %ds...",
                batch_num, attempt, RETRY_DELAY_SEC,
            )
            time.sleep(RETRY_DELAY_SEC)

    raise RuntimeError("Unreachable")  # pragma: no cover
