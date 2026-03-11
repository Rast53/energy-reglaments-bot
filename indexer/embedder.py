from __future__ import annotations

import logging
import time

from openai import OpenAI

from indexer.models import Chunk

logger = logging.getLogger(__name__)

BATCH_SIZE = 20
RETRY_ATTEMPTS = 3
RETRY_DELAY_SEC = 5


def _create_client(api_key: str) -> OpenAI:
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def embed_chunks(
    chunks: list[Chunk],
    api_key: str,
    model: str = "openai/text-embedding-3-large",
) -> list[list[float]]:
    """Embed chunk texts in batches via OpenRouter. Returns vectors in input order."""
    client = _create_client(api_key)
    all_vectors: list[list[float]] = []

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        texts = [c.text for c in batch]

        vectors = _embed_with_retry(client, model, texts, batch_num=i // BATCH_SIZE + 1)
        all_vectors.extend(vectors)

    logger.info("Embedded %d chunks total", len(all_vectors))
    return all_vectors


def _embed_with_retry(
    client: OpenAI,
    model: str,
    texts: list[str],
    batch_num: int,
) -> list[list[float]]:
    """Call embeddings API with retries on failure."""
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = client.embeddings.create(model=model, input=texts)
            sorted_data = sorted(response.data, key=lambda d: d.index)
            vectors = [d.embedding for d in sorted_data]
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
