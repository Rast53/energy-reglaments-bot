from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass


@dataclass
class Chunk:
    doc_id: str
    doc_title: str
    appendix_num: str | None
    version_id: str
    valid_from: str
    valid_until: str | None
    status: str
    is_current: bool
    is_changes_table: bool
    section: str
    section_title: str
    text: str
    chunk_index: int
    source_url: str
    file_hash: str
    point_id: str = ""

    def __post_init__(self) -> None:
        if not self.point_id:
            self.point_id = make_point_id(
                self.doc_id, self.version_id, self.chunk_index
            )


def make_point_id(doc_id: str, version_date: str, chunk_index: int) -> str:
    raw = f"{doc_id}:{version_date}:{chunk_index}".encode()
    return str(uuid.UUID(hashlib.md5(raw).hexdigest()))  # noqa: S324
