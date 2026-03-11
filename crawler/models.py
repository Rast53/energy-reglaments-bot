from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class Document:
    doc_id: str
    title: str
    source_url: str
    appendix_num: str | None = None
    id: int | None = None
    created_at: datetime | None = None


@dataclass
class DocumentVersion:
    doc_id: str
    version_date: date
    status: str
    valid_from: date
    pdf_url: str | None = None
    docx_url: str | None = None
    changes_url: str | None = None
    valid_until: date | None = None
    ns_date: date | None = None
    file_path: str | None = None
    file_hash: str | None = None
    indexed_at: datetime | None = None
    id: int | None = None
    created_at: datetime | None = None
