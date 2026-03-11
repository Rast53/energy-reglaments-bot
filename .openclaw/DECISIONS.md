# Architecture Decisions

## ADR-001: text-embedding-3-large via OpenRouter (2026-03-11)

**Decision:** Use `openai/text-embedding-3-large` via OpenRouter for embeddings.

**Context:** Gemini Embedding 2 (natively multimodal, better quality) was released 2026-03-10 but is not yet available on OpenRouter. Will migrate when available.

**Consequences:** $0.13/1M tokens. For ~71 docs × ~50 chunks × ~300 tokens = ~1M tokens initial indexing ≈ $0.13. Acceptable.

---

## ADR-002: OpenClaw sidecar for LLM (2026-03-11)

**Decision:** Use OpenClaw as LLM sidecar (same pattern as 1c-docs-bot).

**Context:** Direct LLM calls produce lower quality answers. OpenClaw provides better query understanding, structured response format, and easy model switching.

**Consequences:** Extra container in stack. Worth it for answer quality.

---

## ADR-003: Verification Variant B first (2026-03-11)

**Decision:** Implement source validation (Variant B) in MVP. Variant A (critic agent) as Issue #7.

**Context:** Variant B is deterministic and cheap (one LLM call). Variant A adds quality for low-confidence answers but costs 2x LLM calls. Will add Variant A when traffic justifies it.

---

## ADR-004: requests with verify=False for np-sr.ru (2026-03-11)

**Decision:** Use `requests.get(url, verify=False)` for all np-sr.ru requests.

**Context:** np-sr.ru has SSL certificate issues. Playwright not needed — plain HTTP works with SSL verification disabled. Tested: 200 OK with verify=False.

---

## ADR-005: Structural chunking by section numbers (2026-03-11)

**Decision:** Chunk PDFs by section numbers (regex: `^\d+\.\d+`) not by token count.

**Context:** Legal documents have cross-references ("see section 5.2.1"). Token-based chunking splits related content. Section-based preserves legal structure.

**Consequences:** Variable chunk sizes. Handle: min 50 tokens (merge with neighbor), max 400 tokens (split by paragraph keeping section prefix).
