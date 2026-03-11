from __future__ import annotations

import logging
import re
import time
from datetime import date

import requests
import urllib3
from bs4 import BeautifulSoup, Tag

from crawler.models import Document, DocumentVersion

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

DEFAULT_DELAY_SEC = 2


def _get(url: str, verify: bool = False) -> requests.Response:
    resp = requests.get(url, headers=HEADERS, verify=verify, timeout=30)
    resp.raise_for_status()
    return resp


def _parse_date(text: str) -> date | None:
    """Parse date from text, preferring 'Дата вступления в силу: DD.MM.YYYY'."""
    # First try to extract date right after "вступления в силу"
    match = re.search(
        r"вступлени[яе]\s+в\s+силу[:\s]+(\d{2})\.(\d{2})\.(\d{4})",
        text,
        re.IGNORECASE,
    )
    if not match:
        # Fallback: first DD.MM.YYYY in text
        match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
    if not match:
        return None
    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    try:
        return date(year, month, day)
    except ValueError:
        logger.warning("Invalid date: %s", text)
        return None


def _extract_appendix_num(title: str) -> str | None:
    """Extract appendix number like '1', '1.1', '11.1.1' from title."""
    match = re.search(r"Приложение\s*№?\s*([\d.]+)", title, re.IGNORECASE)
    if match:
        return match.group(1).rstrip(".")
    return None


def _make_doc_id(appendix_num: str | None, page_id: str) -> str:
    if appendix_num:
        return f"appendix_{appendix_num.replace('.', '_')}"
    return f"doc_{page_id}"


def _extract_page_id(url: str) -> str:
    """Extract numeric page ID from URL like /reglaments/all/1956."""
    match = re.search(r"/(\d+)(?:\.\w+)?$", url)
    return match.group(1) if match else url.rstrip("/").split("/")[-1]


def fetch_doc_list(base_url: str, delay_sec: float = DEFAULT_DELAY_SEC) -> list[Document]:
    """Parse index page and return list of reglament documents."""
    index_url = f"{base_url}/ru/regulation/joining/reglaments/index.htm"
    logger.info("Fetching document list from %s", index_url)

    resp = _get(index_url)
    soup = BeautifulSoup(resp.content, "html.parser")
    documents: list[Document] = []

    links = soup.find_all("a", href=re.compile(r"/reglaments/(?:\w+/)?(\d+)$"))
    seen_urls: set[str] = set()

    for link in links:
        href = link.get("href", "")
        if not href:
            continue

        full_url = href if href.startswith("http") else f"{base_url}{href}"

        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        title = link.get_text(strip=True)
        if not title:
            continue

        page_id = _extract_page_id(href)
        appendix_num = _extract_appendix_num(title)
        doc_id = _make_doc_id(appendix_num, page_id)

        documents.append(
            Document(
                doc_id=doc_id,
                title=title,
                source_url=full_url,
                appendix_num=appendix_num,
            )
        )

    logger.info("Found %d documents", len(documents))
    time.sleep(delay_sec)
    return documents


def _determine_statuses(dates: list[date]) -> list[str]:
    """Determine status for each version based on valid_from dates.

    Versions are expected sorted newest-first.
    """
    today = date.today()
    statuses: list[str] = []

    sorted_dates = sorted(enumerate(dates), key=lambda x: x[1])
    idx_map: dict[int, str] = {}

    current_idx: int | None = None
    for i, (orig_idx, d) in enumerate(sorted_dates):
        if d > today:
            idx_map[orig_idx] = "future"
        else:
            next_date = sorted_dates[i + 1][1] if i + 1 < len(sorted_dates) else None
            if next_date is None or next_date > today:
                current_idx = orig_idx
                idx_map[orig_idx] = "current"
            else:
                idx_map[orig_idx] = "archive"

    if current_idx is None:
        for i, (orig_idx, d) in enumerate(sorted_dates):
            if d <= today:
                idx_map[orig_idx] = "current"
                break

    for i in range(len(dates)):
        statuses.append(idx_map.get(i, "archive"))

    return statuses


def _compute_valid_until(
    dates: list[date], statuses: list[str]
) -> list[date | None]:
    """Compute valid_until for each version."""
    sorted_by_date = sorted(range(len(dates)), key=lambda i: dates[i])
    valid_until: list[date | None] = [None] * len(dates)

    for pos, idx in enumerate(sorted_by_date):
        if pos + 1 < len(sorted_by_date):
            next_idx = sorted_by_date[pos + 1]
            valid_until[idx] = dates[next_idx]

    return valid_until


def fetch_versions(
    doc: Document,
    base_url: str,
    delay_sec: float = DEFAULT_DELAY_SEC,
) -> list[DocumentVersion]:
    """Parse document page and extract all versions."""
    logger.info("Fetching versions for %s from %s", doc.doc_id, doc.source_url)

    resp = _get(doc.source_url)
    soup = BeautifulSoup(resp.content, "html.parser")
    versions: list[DocumentVersion] = []

    version_blocks = _find_version_blocks(soup)

    if not version_blocks:
        logger.warning("No version blocks found for %s", doc.doc_id)
        return []

    dates: list[date] = []
    raw_versions: list[dict[str, str | date | None]] = []

    for block in version_blocks:
        block_text = block.get_text(" ", strip=True)
        valid_from = _parse_date(block_text)
        if not valid_from:
            continue

        pdf_url = _find_link(block, base_url, r"\.pdf")
        docx_url = _find_link(block, base_url, r"\.docx?")
        changes_url = _find_link_by_text(block, base_url, r"(?:таблиц|изменен)")

        dates.append(valid_from)
        raw_versions.append({
            "valid_from": valid_from,
            "pdf_url": pdf_url,
            "docx_url": docx_url,
            "changes_url": changes_url,
        })

    if not dates:
        logger.warning("No valid dates found for %s", doc.doc_id)
        return []

    statuses = _determine_statuses(dates)
    valid_until_list = _compute_valid_until(dates, statuses)

    for i, raw in enumerate(raw_versions):
        vf = raw["valid_from"]
        assert isinstance(vf, date)
        versions.append(
            DocumentVersion(
                doc_id=doc.doc_id,
                version_date=vf,
                status=statuses[i],
                valid_from=vf,
                valid_until=valid_until_list[i],
                pdf_url=str(raw["pdf_url"]) if raw["pdf_url"] else None,
                docx_url=str(raw["docx_url"]) if raw["docx_url"] else None,
                changes_url=str(raw["changes_url"]) if raw["changes_url"] else None,
            )
        )

    logger.info(
        "Found %d versions for %s (current=%d, future=%d, archive=%d)",
        len(versions),
        doc.doc_id,
        sum(1 for v in versions if v.status == "current"),
        sum(1 for v in versions if v.status == "future"),
        sum(1 for v in versions if v.status == "archive"),
    )
    time.sleep(delay_sec)
    return versions


def _find_version_blocks(soup: BeautifulSoup) -> list[Tag]:
    """Find blocks that represent individual versions on the page.

    Anchors on 'Дата вступления в силу' text — each such node is a version entry.
    Walks up to a container that also has a PDF/DOC link.
    """
    candidates: list[Tag] = []
    seen: set[int] = set()

    # Primary strategy: find "Дата вступления в силу" anchors
    for node in soup.find_all(string=re.compile(r"Дата вступления в силу", re.IGNORECASE)):
        # Walk up to find a container that has both a date and a file link
        parent: Tag | None = node.find_parent(["div", "td", "li", "p", "tr"])
        while parent is not None:
            has_pdf = parent.find("a", href=re.compile(r"\.(pdf|doc)", re.IGNORECASE))
            has_date = re.search(r"\d{2}\.\d{2}\.\d{4}", parent.get_text())
            if has_pdf and has_date:
                if id(parent) not in seen:
                    seen.add(id(parent))
                    candidates.append(parent)
                break
            parent = parent.find_parent(["div", "td", "li", "p", "tr"])

    if candidates:
        return candidates

    # Fallback: look for small blocks (< 600 chars) with both a date and a file link
    fallback: list[Tag] = []
    for tag in soup.find_all(["div", "td", "li"]):
        text = tag.get_text(" ", strip=True)
        if (
            re.search(r"\d{2}\.\d{2}\.\d{4}", text)
            and tag.find("a", href=re.compile(r"\.(pdf|doc)", re.IGNORECASE))
            and len(text) < 600
            and id(tag) not in seen
        ):
            seen.add(id(tag))
            fallback.append(tag)
    return _deduplicate_blocks(fallback)


def _deduplicate_blocks(blocks: list[Tag]) -> list[Tag]:
    """Remove nested blocks, keeping only innermost (smallest) ones."""
    result: list[Tag] = []
    for block in blocks:
        is_parent = any(
            block != other and other in block.descendants
            for other in blocks
        )
        if not is_parent:
            result.append(block)
    return result


def _find_link(tag: Tag, base_url: str, pattern: str) -> str | None:
    """Find first link matching href pattern."""
    link = tag.find("a", href=re.compile(pattern, re.IGNORECASE))
    if link and isinstance(link, Tag):
        href = link.get("href", "")
        if isinstance(href, str) and href:
            return href if href.startswith("http") else f"{base_url}{href}"
    return None


def _find_link_by_text(tag: Tag, base_url: str, text_pattern: str) -> str | None:
    """Find link whose text matches a pattern."""
    for link in tag.find_all("a", href=True):
        if isinstance(link, Tag):
            link_text = link.get_text(strip=True)
            if re.search(text_pattern, link_text, re.IGNORECASE):
                href = link.get("href", "")
                if isinstance(href, str) and href:
                    return href if href.startswith("http") else f"{base_url}{href}"
    return None
