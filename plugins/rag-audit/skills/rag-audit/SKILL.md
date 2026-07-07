---
name: rag-audit
description: Structural audit ("linter") for RAG pipelines. Use whenever the user asks to review, audit, improve, or debug a RAG system — or complains about RAG answer quality, hallucination, irrelevant retrieval, or "the chatbot keeps answering wrong". Also use when asked to check chunking, embeddings, retrieval configuration, RAG prompts, or evaluation readiness, even if the word "audit" never appears. Triggers include /rag-audit:audit and natural-language requests like "review my RAG chatbot structure", "내 RAG 챗봇 구조 좀 봐줘", or "why does my bot hallucinate".
---

# RAG Audit

Audit the structure of a RAG (Retrieval-Augmented Generation) pipeline and report findings the way a linter would: stable rule IDs, severity levels, `file:line` evidence, and a concrete fix for each finding.

## What this skill produces

One audit report (exact template in Step 5) containing:

1. **Structure Score** — 0–100 overall + per-category, computed mechanically from the rule verdicts (formula in `references/rules.md`)
2. **Pipeline Inventory** — where each RAG stage lives in the code
3. **Findings** — rule violations with evidence and fixes
4. **Measure next** — the shortest path from "structure looks right" to "quality is measured"

## Non-negotiable principles

These exist because LLM-generated reviews tend to be inconsistent between runs and confident without evidence. The rules below are what make this audit trustworthy:

1. **Evidence or silence.** Every finding cites `file:line` (or a config key / dependency entry). If you cannot point at code, do not report the finding — mark the rule `UNKNOWN` instead. Never infer a violation from what code "probably" does.
2. **Full rule coverage.** Evaluate every rule in `references/rules.md`, in catalog order, every time. Each rule ends in exactly one state: `PASS`, `FINDING`, `N/A` (one-line reason), or `UNKNOWN` (could not determine). Forced coverage is what keeps two runs of this audit consistent with each other.
3. **Scores are computed, never felt.** The only score in the report is the Structure Score defined in `references/rules.md`: a deterministic, severity-weighted PASS ratio over the rule verdicts. Never adjust the number by impression, and never output any other rating (letter grades, stars, per-finding points). Label it honestly: structural readiness — a lower bound when UNKNOWNs exist — not measured answer quality.
4. **State the static limits.** The report must say plainly: this audit checks structure, not measured answer quality. A structurally clean pipeline can still retrieve garbage, and only measurement can tell.
5. **Report language follows the user.** Write the report in the language the user is speaking (Korean user → Korean report). Rule IDs, severity labels, and code stay in English.
6. **Read-only.** Never modify the target repository during the audit. Present fixes as snippets/diffs inside the report; apply them only if the user asks afterward.
7. **Terse output.** Everything you say lives inside the report template — no narration while auditing, no essay after it. Detail is severity-proportional: CRITICAL/WARN findings get three lines each, INFO findings one line, coverage one line per verdict class. A typical single-pipeline report fits on one screen; extra length is a defect, not thoroughness.

## Workflow

### Step 0 — Scope the target

Identify which directory/service contains the RAG pipeline. In monorepos or multi-service repos, list the candidates (look for vector-store dependencies, embedding calls, prompt template files) and ask the user to pick one. Audit exactly one pipeline per report.

### Step 1 — Detect the stack

Check dependency manifests: `requirements.txt`, `pyproject.toml`, `package.json`, `build.gradle`, `pom.xml`, `go.mod`.

| Signal in dependencies | Adapter to read |
|---|---|
| `langchain*`, `@langchain/*`, `langgraph` | `references/langchain.md` |
| anything else, or no framework at all | `references/generic.md` |

Additional adapters (LlamaIndex, Spring AI, Haystack, ...) will be added as reference files over time. If several frameworks appear, read every matching adapter. If a framework is detected but has no adapter yet, use `references/generic.md` and say so in the report.

### Step 2 — Read the adapter and the rule catalog

Read the matching adapter file AND `references/rules.md` in full before judging anything. The adapter tells you *where* each concept lives in this framework; the catalog tells you *what* to check. Do not audit from memory of what LangChain "usually" looks like — APIs change and projects deviate.

### Step 3 — Build the Pipeline Inventory (before any judgment)

Locate each stage and record evidence. Important: ingestion code frequently lives outside the serving path. Before concluding a stage is missing, search for one-off scripts and notebooks — file names containing `ingest`, `index`, `embed`, `load`, `etl`, `pipeline`, and any `*.ipynb`.

| Stage | Where (file:line) | Key config observed |
|---|---|---|
| Ingestion & chunking | | splitter type, chunk size, overlap |
| Embedding | | model name, same model for docs & queries? |
| Vector store | | store, distance metric, persistence |
| Retrieval | | k, threshold, hybrid?, reranker?, filters |
| Query handling | | multi-turn rewrite / condensation? |
| Prompt & generation | | template location, generation model |
| Observability | | tracing, chunk logging, feedback capture |
| Evaluation | | golden set, CI evals, scoring |

`NOT FOUND` is a legitimate value — record it rather than guessing. The inventory is built first precisely so that findings are grounded in a map of the code, not in impressions.

### Step 4 — Apply the rules

Go through `references/rules.md` category by category (C → E → R → P → O → V). For each rule, decide PASS / FINDING / N/A / UNKNOWN using the inventory plus targeted code reading.

Severity defaults are in the catalog. Escalate or downgrade only with a stated, codebase-specific reason — e.g., RAG-R003 (dense-only retrieval) escalates to CRITICAL when the corpus is dense with product codes, internal jargon, or Korean proper nouns that embedding models handle poorly.

### Step 5 — Score and write the report

Compute the Structure Score (overall and per category) from the verdicts, exactly as specified in the Scoring section of `references/rules.md` — no judgment adjustments. Then write the report.

ALWAYS use this exact template, and write nothing outside it:

```markdown
# RAG Audit — <target>

**Structure Score: <N>/100** · <X> CRITICAL / <Y> WARN / <Z> INFO · determined <d>/30
<one line: stack, pipeline shape, and the 2–3 rule IDs to fix first.
If UNKNOWN > 0, append: "score reads as a lower bound.">

| Category | Score | PASS / FINDING / UNKNOWN (N/A excluded) |
|---|---|---|
| C · Chunking & Ingestion | | |
| E · Embedding | | |
| R · Retrieval | | |
| P · Prompt & Generation | | |
| O · Observability | | |
| V · Evaluation readiness | | |

<only if a severity was escalated/downgraded (e.g., R003 → CRITICAL): one line with the reason>

## Inventory
<the table from Step 3 — a few words per cell, no sentences>

## Findings
<sorted CRITICAL → WARN → INFO>

<CRITICAL and WARN: exactly this three-line shape —>
### [SEVERITY] RAG-X000 · <rule title> — `path/file.py:41`
<one sentence: what the code does and why that hurts THIS codebase>
**Fix:** <one line; a snippet (≤5 lines) only when exact wording matters, e.g. prompt text>

<INFO: exactly one line each —>
- [INFO] RAG-X000 <title> — `file:line` · Fix: <half a line>

## Coverage
PASS: RAG-C003 (ingest.py:24) · RAG-R001 (k=4) · <...>
N/A: RAG-R006 (single-turn) · <...>
UNKNOWN: RAG-E003 (no index metadata found) · <...>

## Measure next
<up to 3 one-line steps toward measuring answer quality, chosen from what failed —
typical ladder: chunk logging (O001) → 50-question golden set incl. unanswerable
(V001/V004) → one claim-level faithfulness check (V003).>
<one closing sentence per Principle 4: this audit checks structure — answer
quality itself only shows up in measurement.>
```

### Step 6 — Offer follow-up

One line, at most: offer to apply a fix, deep-dive a finding, or scaffold "Measure next". Do not start fixing unprompted.

## Reference files

- `references/rules.md` — the rule catalog. Read fully on every audit.
- `references/langchain.md` — LangChain / LangGraph detection map (Python & JS).
- `references/generic.md` — fallback detection strategy for unknown stacks.
