from __future__ import annotations

import logging
from dataclasses import asdict

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    Distance,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from indexer.models import Chunk

logger = logging.getLogger(__name__)

UPSERT_BATCH_SIZE = 100


def get_qdrant_client(url: str) -> QdrantClient:
    return QdrantClient(url=url)


def ensure_collection(
    client: QdrantClient,
    name: str,
    vector_size: int = 3072,
) -> None:
    """Create collection if it doesn't exist and set up payload indexes."""
    try:
        client.get_collection(name)
        logger.info("Collection '%s' already exists", name)
    except (UnexpectedResponse, Exception):
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )
        logger.info("Created collection '%s' (dim=%d, COSINE)", name, vector_size)

    _ensure_payload_indexes(client, name)


def _ensure_payload_indexes(client: QdrantClient, collection_name: str) -> None:
    indexes = {
        "is_current": PayloadSchemaType.BOOL,
        "status": PayloadSchemaType.KEYWORD,
        "doc_id": PayloadSchemaType.KEYWORD,
        "valid_from": PayloadSchemaType.KEYWORD,
    }
    for field, schema_type in indexes.items():
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=schema_type,
            )
            logger.info("Created index '%s' on '%s'", field, collection_name)
        except (UnexpectedResponse, Exception):
            logger.debug("Index '%s' likely already exists", field)


def _chunk_to_payload(chunk: Chunk) -> dict:
    payload = asdict(chunk)
    payload.pop("point_id", None)
    return payload


def upsert_points(
    client: QdrantClient,
    collection: str,
    chunks: list[Chunk],
    vectors: list[list[float]],
) -> None:
    """Upsert chunk vectors into Qdrant in batches."""
    points = [
        PointStruct(
            id=chunk.point_id,
            vector=vector,
            payload=_chunk_to_payload(chunk),
        )
        for chunk, vector in zip(chunks, vectors)
    ]

    for i in range(0, len(points), UPSERT_BATCH_SIZE):
        batch = points[i : i + UPSERT_BATCH_SIZE]
        client.upsert(collection_name=collection, points=batch)
        logger.info(
            "Upserted %d points into '%s' (%d/%d)",
            len(batch), collection, min(i + UPSERT_BATCH_SIZE, len(points)), len(points),
        )
