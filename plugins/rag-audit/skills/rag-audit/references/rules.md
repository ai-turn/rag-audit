# RAG Audit Rule Catalog — v0.2

Rules are framework-agnostic: they name *concepts*, not APIs. The adapter files map each concept to framework-specific code. Every audit evaluates every rule, in this order.

Severity meanings:

- **CRITICAL** — likely producing wrong/hallucinated answers right now, or making quality permanently unmeasurable
- **WARN** — probable quality or robustness loss; fix soon
- **INFO** — improvement opportunity or missing maturity practice

## Scoring

The report includes a **Structure Score (0–100)**, computed mechanically from the rule verdicts — never adjusted by judgment. It measures structural readiness, not measured answer quality.

- Weights by **applied** severity (after any escalation/downgrade): CRITICAL = 8, WARN = 3, INFO = 1
- `PASS` earns the rule's weight; `FINDING` and `UNKNOWN` earn 0; `N/A` rules are excluded from the calculation entirely
- **Score = round(100 × earned weight ÷ total weight of all non-N/A rules)**
- Compute a per-category score with the same formula within each category — that is what shows *where* the pipeline is weak
- Always report determination coverage alongside (e.g., "determined 26/30"); since UNKNOWN earns 0, the score is a lower bound when UNKNOWNs exist
- Interpretation guide: 90+ structurally solid · 60–89 fix findings top-down · below 60 fundamental gaps

Contents: C Chunking & Ingestion (C001–C005) · E Embedding (E001–E003) · R Retrieval (R001–R008) · P Prompt & Generation (P001–P006) · O Observability (O001–O004) · V Evaluation readiness (V001–V004)

---

## C — Chunking & Ingestion

### RAG-C001 · No chunk overlap
- **Severity:** WARN
- **Check:** splitter configured with overlap of 0, or an unset parameter that defaults to 0.
- **Why:** facts that straddle a chunk boundary are split into two unretrievable halves; queries landing near boundaries degrade silently.
- **Fix:** set overlap to roughly 10–20% of chunk size.

### RAG-C002 · Structure-blind splitting
- **Severity:** WARN
- **Check:** fixed-size character splitting applied to structured sources (Markdown, HTML, code, tables) when a structure-aware splitter is available.
- **Why:** headings, code blocks, and table rows get cut mid-unit; the chunk loses the context that made it meaningful.
- **Fix:** split on structural boundaries first (headers, code blocks), then size-limit within sections.

### RAG-C003 · Metadata dropped at ingestion
- **Severity:** WARN
- **Check:** source, title, section, URL, or updated-at metadata available at load time but not stored on chunks.
- **Why:** without metadata there is no filtering (R005), no citation (P004), and no way to trace a bad answer back to its document.
- **Fix:** propagate loader metadata onto every chunk; add section titles during splitting.

### RAG-C004 · Token/character mismatch on CJK text
- **Severity:** WARN
- **Check:** chunk sizes defined in characters while downstream budgets (context window, embedding input limit) are in tokens — or vice versa — on Korean/CJK corpora.
- **Why:** Korean averages far more tokens per character than English; a "1000-char" chunk can be 2–3× the token budget you assumed, causing truncation or overflow.
- **Fix:** size chunks with the tokenizer of the embedding/generation model, or set character sizes calibrated against measured token counts for the actual corpus.

### RAG-C005 · No re-indexing / dedup strategy
- **Severity:** INFO
- **Check:** no idempotent upsert (stable IDs), no dedup, and no defined procedure for re-ingesting updated documents.
- **Why:** re-running ingestion duplicates chunks; stale chunks answer alongside fresh ones and the two are indistinguishable.
- **Fix:** derive stable chunk IDs (doc ID + position or content hash); delete-then-insert per document on update.

---

## E — Embedding

### RAG-E001 · Embedding model unsuited to corpus language
- **Severity:** CRITICAL
- **Check:** monolingual/English-centric embedding model (e.g., `all-MiniLM-L6-v2`) over a mostly non-English (e.g., Korean) corpus.
- **Why:** retrieval quality collapses quietly — nothing errors, similarity scores just stop meaning anything.
- **Fix:** use a multilingual or language-matched embedding model (e.g., `bge-m3`, `multilingual-e5`, `text-embedding-3-large`, or a Korean-specialized model); re-embed the corpus after switching.

### RAG-E002 · Query/document embedding mismatch
- **Severity:** CRITICAL
- **Check:** different model, version, dimension, or normalization between index time and query time. Watch for ingestion living in a separate script with its own config.
- **Why:** vectors from different models share no geometry; retrieval becomes near-random while still returning confident top-k results.
- **Fix:** single source of truth for the embedding config, imported by both ingestion and serving paths.

### RAG-E003 · No embedding version management
- **Severity:** INFO
- **Check:** no record of which embedding model/version built the index; no rebuild plan for model changes.
- **Why:** upgrading the embedding model without a full re-index silently creates an E002 situation.
- **Fix:** store the model identifier in index/collection metadata; treat model change as a migration that rebuilds the index.

---

## R — Retrieval

### RAG-R001 · Unjustified top-k extremes
- **Severity:** WARN
- **Check:** k=1–2 (fragile: one bad hit means no fallback), or k>10 with no reranking (noise floods the context).
- **Why:** k is the single biggest lever on the precision/recall balance of the context, and extreme values are rarely deliberate.
- **Fix:** k in the 3–8 range as a default; larger k only in a retrieve-then-rerank design (see R004).

### RAG-R002 · No relevance threshold
- **Severity:** WARN
- **Check:** pipeline always passes top-k to the prompt regardless of relevance; no score cutoff, no LLM relevance-judgment step on the retrieved chunks, and no emptiness handling.
- **Why:** when the corpus has no answer, top-k still returns the *least irrelevant* chunks, and the model will confabulate from them. This is the retrieval half of hallucination (the prompt half is P003).
- **Fix:** apply a score threshold, an emptiness check, or an LLM relevance gate (judge retrieved chunks against the question before generation — costs one extra call per request); route "nothing relevant" to an explicit no-answer path.

### RAG-R003 · Dense-only retrieval
- **Severity:** WARN (escalate to CRITICAL if the corpus is heavy with IDs, product codes, error strings, or proper nouns)
- **Check:** vector similarity is the only retrieval signal — no BM25/keyword leg, no hybrid fusion.
- **Why:** embeddings blur exact identifiers; a query for `KDNS-1042` or a specific error message retrieves "similar vibes" instead of the exact document.
- **Fix:** add a lexical retriever and fuse (e.g., RRF or weighted ensemble); many vector stores now ship hybrid search natively.

### RAG-R004 · No reranking stage
- **Severity:** INFO (WARN when k > 6)
- **Check:** retrieved chunks go straight into the prompt in vector-score order, with no cross-encoder/reranker pass.
- **Why:** bi-encoder similarity is a coarse first pass; rerankers substantially improve precision of what actually enters the context.
- **Fix:** retrieve wide (k=20), rerank to 3–5 with a cross-encoder or reranking API.

### RAG-R005 · Available metadata unused for filtering
- **Severity:** INFO
- **Check:** chunks carry filterable metadata (product, version, language, date) but queries never apply filters.
- **Why:** cross-product or cross-version contamination — the right answer for product A is a wrong answer for product B.
- **Fix:** apply metadata filters derived from the query or session context before similarity search.

### RAG-R006 · Multi-turn queries retrieved verbatim
- **Severity:** WARN
- **Check:** in a conversational bot, follow-up utterances ("그럼 두 번째는?", "what about that one?") are embedded as-is with no query rewriting/condensation against chat history.
- **Why:** the follow-up alone carries almost no retrievable signal; retrieval quality craters from turn 2 onward — a top complaint pattern in production chatbots.
- **Fix:** condense (history + follow-up) into a standalone query before retrieval, or use a history-aware retriever.
- **N/A when:** the application is genuinely single-turn.

### RAG-R007 · No query preprocessing for retrieval
- **Severity:** INFO
- **Check:** the raw user utterance is embedded/searched verbatim — no cleanup, no multi-query expansion, no hypothetical-answer (HyDE) step, and no condensation anywhere before retrieval.
- **Why:** raw utterances carry filler and phrasing noise that dilute vector similarity, and a single formulation gambles recall on one wording. Cleanup, expansion, and HyDE each cover a different miss mode.
- **Fix:** start with query cleanup; add multi-query expansion or HyDE only where recall measurably lags — each variant adds latency and tokens, and HyDE can mislead on niche corpora. No specific technique is required; the finding is having no strategy at all.

### RAG-R008 · Hybrid scores fused by raw arithmetic
- **Severity:** WARN
- **Check:** lexical and dense results merged by adding or averaging raw scores. BM25 scores and cosine similarities live on different scales.
- **Why:** one leg silently dominates and the hybrid stops doing its job — ranking drifts toward whichever score scale happens to be larger, and nothing errors.
- **Fix:** fuse by rank, not by score: RRF (Reciprocal Rank Fusion) or a normalized weighted ensemble. Store-native hybrid modes and LangChain's `EnsembleRetriever` already fuse this way.
- **N/A when:** retrieval is single-leg (no hybrid — that territory is R003's).

---

## P — Prompt & Generation

### RAG-P001 · Context not clearly delimited
- **Severity:** WARN
- **Check:** retrieved chunks concatenated into the prompt without delimiters/tags separating them from instructions and the user question.
- **Why:** the model cannot reliably distinguish authoritative context from user input; instruction-injection via documents also becomes easier.
- **Fix:** wrap context in explicit delimiters (e.g., XML-style tags), one clearly separated block per chunk, ideally with source labels.

### RAG-P002 · No grounding instruction
- **Severity:** CRITICAL
- **Check:** prompt never instructs the model to answer *from the provided context* (and to prefer it over prior knowledge).
- **Why:** without it the model freely mixes parametric memory with retrieved facts, producing plausible answers your documents never said.
- **Fix:** add an explicit grounding instruction; require that claims be supported by the context.

### RAG-P003 · No unanswerable handling
- **Severity:** CRITICAL
- **Check:** prompt has no instruction for the "context doesn't contain the answer" case.
- **Why:** this is the prompt half of hallucination (pair of R002): the model will answer anyway. "모르면 모른다고" must be an instructed behavior, not a hope.
- **Fix:** instruct an explicit refusal/deflection response when the context is insufficient; give the exact wording to use.

### RAG-P004 · No citation instruction
- **Severity:** INFO
- **Check:** answers carry no source attribution even though chunk metadata exists.
- **Why:** citations let users verify and let developers debug which chunk produced which claim; they also raise user trust.
- **Fix:** label chunks with IDs in the prompt and instruct the model to reference them.

### RAG-P005 · No context-length guard
- **Severity:** WARN
- **Check:** no token counting or truncation before prompt assembly; context size = k × chunk size and grows unchecked (with chat history on top).
- **Why:** overflow errors at best; silent truncation of the most relevant chunk at worst.
- **Fix:** budget tokens per section (system / context / history / question) and trim deterministically, dropping lowest-ranked chunks first.

### RAG-P006 · Context ordering ignores position effects
- **Severity:** INFO
- **Check:** chunks placed in arbitrary or worst-relevance-first order.
- **Why:** models attend more reliably to the beginning and end of long contexts ("lost in the middle"); burying the best chunk mid-context wastes it.
- **Fix:** place highest-relevance chunks first; in long contexts, reorder so the best chunks sit at both edges (1·3·5·…·4·2) instead of leaving them buried mid-sequence.

---

## O — Observability

### RAG-O001 · Retrieved chunks not recorded per request
- **Severity:** CRITICAL
- **Check:** logs/traces do not capture *which chunks, with which scores* went into each answer.
- **Why:** this is the load-bearing rule of the category. Without per-request chunk capture, no post-hoc quality analysis is possible: you cannot compute faithfulness, debug a bad answer, or build a golden set from production. Everything in category V depends on this.
- **Fix:** log (or trace) chunk IDs, sources, and scores on every request — as a retriever span in the tracing system, or structured logs keyed by request ID.

### RAG-O002 · No tracing of the pipeline
- **Severity:** WARN
- **Check:** no tracing instrumentation (Langfuse, LangSmith, OpenTelemetry, ...) around retrieval and generation steps.
- **Why:** latency, cost, and failure analysis all require per-stage visibility; a RAG pipeline without traces is debugged by guesswork.
- **Fix:** instrument the serving path with any tracer; ensure the retrieval step is a distinct span (satisfying O001).

### RAG-O003 · No user feedback capture
- **Severity:** INFO
- **Check:** no thumbs up/down, rating, or correction channel attached to answers.
- **Why:** feedback is the cheapest quality signal and the best source of golden-set candidates — negative-feedback traces are exactly the cases worth studying.
- **Fix:** capture a minimal signal (binary is enough) and store it linked to the request/trace ID.

### RAG-O004 · No per-stage latency/cost visibility
- **Severity:** INFO
- **Check:** no measurement of retrieval vs. generation latency or token cost per request.
- **Why:** optimization without stage-level numbers targets the wrong stage; cost regressions go unnoticed.
- **Fix:** record per-stage duration and token counts (usually free once O002 is done).

---

## V — Evaluation readiness

### RAG-V001 · No golden dataset
- **Severity:** WARN
- **Check:** no curated set of (question, expected context/answer) pairs anywhere in the repo or its docs.
- **Why:** without a fixed test set, every prompt/retriever change is evaluated by vibes; regressions ship silently.
- **Fix:** start with ~50 real user questions (stratified: easy/hard, single/multi-hop, answerable/unanswerable); grow toward 200.

### RAG-V002 · No regression evaluation on changes
- **Severity:** WARN
- **Check:** prompt, retriever, chunking, or model changes merge without any automated evaluation run.
- **Why:** RAG quality is a system property; a "small prompt tweak" can drop faithfulness across the board and nothing in CI will notice.
- **Fix:** run the golden set on every change to prompt/retrieval config; compare against the previous run before merging.

### RAG-V003 · No answer-quality scoring of any kind
- **Severity:** INFO
- **Check:** no faithfulness/relevance scoring exists, online or offline.
- **Why:** structure audits (this tool) find defects, but only measurement tells you whether answers are actually good — and whether fixes helped.
- **Fix:** begin with one metric: claim-level faithfulness (are the answer's claims supported by the retrieved context?) on a sample of traffic, scored pass/fail with a language-matched judge prompt. Validate the judge against ~100 human-labeled examples before trusting it.

### RAG-V004 · Test set lacks unanswerable questions
- **Severity:** INFO
- **Check:** golden set (if present) contains only answerable questions.
- **Why:** refusal behavior (P003) is untested unless the test set includes questions the corpus cannot answer; over-eager answering is the most common uncaught failure.
- **Fix:** make 15–25% of the golden set unanswerable-by-design, with "correct refusal" as the expected output.
