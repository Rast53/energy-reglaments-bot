# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Crawler (cron 02:00 UTC daily)                                  │
│  requests + BeautifulSoup → np-sr.ru (verify=False)             │
│  → downloads PDFs → SHA256 dedup → PostgreSQL versions registry  │
└────────────────────────┬────────────────────────────────────────┘
                         │ new files (indexed_at IS NULL)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Indexer (runs after crawler)                                    │
│  pymupdf4llm → Markdown → structural chunking by section nums   │
│  text-embedding-3-large (OpenRouter) → Qdrant upsert            │
│  sets indexed_at in PostgreSQL                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
           ┌─────────────┴──────────────┐
           ▼                            ▼
    ┌─────────────┐            ┌──────────────────┐
    │   Qdrant    │            │   PostgreSQL      │
    │  collection │            │  documents        │
    │  reglaments │            │  document_versions│
    │  3072 dims  │            │  crawler_log      │
    └──────┬──────┘            └──────────────────┘
           │ semantic search
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Bot (aiogram 3)                                                 │
│  1. detect_mode(text) → current / future / both                 │
│  2. embed(text) → vector (text-embedding-3-large)               │
│  3. qdrant.search(vector, filter=mode) → top-5 chunks           │
│  4. POST /v1/chat/completions → OpenClaw (chunks as context)    │
│  5. parse JSON {answer, sources, confidence, has_future_changes}│
│  6. validate_sources: all sources present in Qdrant results?    │
│  7. format & send to Telegram                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  OpenClaw   │
                    │  (sidecar)  │
                    │  Gemini     │
                    │  Flash      │
                    └─────────────┘
```

## Components as Sinks

Each component is a **sink** — it accepts input, does work, terminates. No cross-triggering.

| Component | Input | Output | Terminates |
|-----------|-------|--------|-----------|
| crawler | HTTP trigger / cron | files/ + PostgreSQL | ✅ yes |
| indexer | PostgreSQL (unindexed) | Qdrant | ✅ yes |
| bot handler | Telegram message | Telegram reply | ✅ yes |

## Versioning Model

```
document_versions table:
  status: current | future | archive
  is_current: bool (redundant fast filter)
  valid_from: date
  valid_until: date | null

Status logic (determined by crawler):
  future  → valid_from > today
  current → valid_from ≤ today AND (no next version OR next.valid_from > today)
  archive → all others
```

## Query Modes

```
detect_mode(text):
  keywords: ["будущ", "изменени", "вступ", "с 1", "с 01",
             "планируется", "предстоящ", "новая редакция"]
  → "future"  if any keyword matches
  → "current" otherwise (default)
  → "both"    if both present
```

## Verification Layer (Variant B)

```python
result = openclaw.chat(context=chunks, question=text)
# result: {answer, sources: [{doc_title, version_date, section}], confidence, ...}

# Validate: every source must be traceable to Qdrant results
valid = all(
    any(chunk.payload.doc_id == s.doc_id and chunk.payload.section == s.section
        for chunk in retrieved_chunks)
    for s in result.sources
)
if not valid:
    result.confidence = "low"

# confidence=low → append disclaimer to answer
```

## Future: Variant A (legal mode)

When implemented (Issue #7):
- User sends `/legal` flag or taps button
- Second OpenClaw call: critic agent verifies answer against chunks
- Up to 2 regeneration attempts
- Response marked ✅ Verified or ⚠️ Needs review
