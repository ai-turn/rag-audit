# Adapter: Generic / Unknown stack (fallback)

Use this when no framework adapter matches, or alongside a framework adapter when much of the pipeline is hand-rolled. The strategy: find each pipeline *concept* by searching for its vocabulary, then audit the surrounding code against the same rules.

## Locating stages by vocabulary

Search (ripgrep/grep, case-insensitive) per stage. Vector-DB client calls are the strongest anchors — find those first, then walk outward.

- **Vector store / retrieval anchor:** client imports and calls for Pinecone, Qdrant, Weaviate, Milvus, Chroma, pgvector (`<=>` operator, `vector` column), Elasticsearch/OpenSearch (`knn`, `dense_vector`), Redis (`FT.SEARCH`, `VECTOR`), FAISS. Also REST calls to `/query`, `/search`, `/points/search`.
- **Chunking:** `chunk`, `split`, `overlap`, `splitter`, `window`, `stride`. Read the function to get size/overlap and the unit (chars vs tokens) [C001, C002, C004].
- **Embedding:** `embed`, `embedding`, `encode(`, model-name strings (`text-embedding`, `bge-`, `e5`, `MiniLM`, `sentence-transformers`). Compare the ingestion-side and query-side call sites [E001, E002].
- **Retrieval params:** `top_k`, `topK`, `limit`, `k=`, `score_threshold`, `min_score`, `similarity`, `alpha` (hybrid weight), `rerank`, `bm25`, `keyword` [R001–R005].
- **Query rewriting:** `condense`, `rewrite`, `standalone`, `history` near the retrieval call [R006].
- **Prompt:** files/strings containing `context`, `참고`, `문서`, system-prompt files (`*.txt`, `*.md`, `prompts/` dirs, YAML prompt keys). Judge P001–P006 on the actual template text.
- **Observability:** `langfuse`, `langsmith`, `opentelemetry`, `otel`, `trace`, `span`, `logger` near retrieval/generation. Verify chunk IDs/scores are actually recorded, not just "retrieved N docs" [O001].
- **Evaluation:** `eval`, `golden`, `testset`, `dataset`, `ragas`, `judge` in code, CI configs (`.github/workflows`), and docs [V001–V003].

## Interpreting hand-rolled code

- A raw SQL/HTTP similarity query with `LIMIT N` is the retrieval stage; N is k [R001]. A `WHERE score > x` or post-filter loop is the threshold [R002].
- Hybrid in custom stacks often appears as *two* queries (one FTS/BM25, one vector) merged in application code — the merge function is the fusion step [R003].
- Prompt assembly by f-string/`+` concatenation is common; judge delimiting [P001] on the final assembled string, and look for any token counting before the LLM call [P005].

## Honesty requirements for this adapter

Custom stacks raise UNKNOWN rates — that is expected and must stay visible:

- Only mark a rule PASS/FINDING when you located the concept's actual code. Vocabulary that never matches → the stage may not exist (inventory `NOT FOUND`) or may be externalized (managed RAG services, e.g., a vendor "retrieval API" — note it and mark dependent rules N/A with a reason).
- In the report's Summary, state that the audit ran on the generic adapter and name any stages whose location you could not confirm.
- If an unrecognized framework is clearly present (imports from one package dominate the pipeline), say so and suggest the user request/contribute an adapter for it.
