# Adapter: LangChain / LangGraph (Python & JS)

This file maps rule-catalog concepts to where they live in LangChain code. Rule IDs in brackets point back to `rules.md`. LangChain projects vary widely (legacy chains, LCEL, LangGraph), so treat these as search starting points, not the only possible spellings.

## Stack signals

- Python: `langchain`, `langchain-core`, `langchain-community`, `langchain-text-splitters`, `langchain-openai`, `langchain-huggingface`, `langgraph` in `requirements.txt` / `pyproject.toml`
- JS/TS: `langchain`, `@langchain/core`, `@langchain/community`, `@langchain/openai`, `@langchain/langgraph` in `package.json`
- Ingestion often lives in a separate script or notebook. Search file names for `ingest`, `index`, `embed`, `load`, `build`, and any `*.ipynb` before marking ingestion NOT FOUND.

## Chunking & Ingestion [C001–C005]

Search for imports from `langchain_text_splitters` (py) / `@langchain/textsplitters` (js).

- `RecursiveCharacterTextSplitter(chunk_size=..., chunk_overlap=...)`, `CharacterTextSplitter(...)` — read `chunk_overlap` directly [C001]. Note the length unit: default `len` counts characters; `.from_tiktoken_encoder(...)` counts tokens [C004].
- Plain `CharacterTextSplitter`/`RecursiveCharacterTextSplitter` over Markdown/HTML/code sources while `MarkdownHeaderTextSplitter`, `HTMLHeaderTextSplitter`, or `RecursiveCharacterTextSplitter.from_language(...)` go unused → [C002].
- Loaders (`PyPDFLoader`, `WebBaseLoader`, `DirectoryLoader`, ...) produce `Document(page_content, metadata)`. Check that splitter output keeps `metadata` and that ingestion doesn't rebuild `Document(page_content=...)` while dropping the metadata dict [C003].
- Upserts: `vectorstore.add_documents(docs)` without `ids=` (or without a delete-by-source step first) → duplicates on re-run [C005].

## Embedding [E001–E003]

- `OpenAIEmbeddings(model=...)`, `HuggingFaceEmbeddings(model_name=...)`, `OllamaEmbeddings(...)`, etc. Judge the model name against corpus language: `all-MiniLM-*`, `all-mpnet-*` are English-centric [E001 on Korean corpora]; `bge-m3`, `multilingual-e5-*`, `text-embedding-3-*` are multilingual.
- E002 in LangChain is almost always a *two-file* bug: the ingestion script constructs its own embeddings object, the server constructs another. Compare model names/params across both. Also check `Chroma(persist_directory=..., embedding_function=...)` / `FAISS.load_local(...)` calls — a persisted index built by an older script with a different model is a silent E002/E003.
- Index metadata rarely records the model in LangChain projects; if nothing pins it (config file, collection metadata), flag [E003].

## Retrieval [R001–R006]

Primary surface: `vectorstore.as_retriever(search_type=..., search_kwargs={...})`.

- `search_kwargs={"k": N}` → judge N per [R001]. Default k when unset is typically 4 (PASS-ish, but note it's implicit).
- `search_type="similarity_score_threshold"` + `score_threshold` in kwargs → R002 PASS. Plain `"similarity"` with no downstream emptiness check → [R002] FINDING. Also accept manual patterns: `similarity_search_with_score(...)` followed by a score filter.
- Hybrid [R003]: look for `EnsembleRetriever` combining `BM25Retriever` with the vector retriever, or store-native hybrid (e.g., Weaviate/OpenSearch hybrid modes, `pgvector` + FTS). Dense retriever alone → FINDING.
- Reranking [R004]: `ContextualCompressionRetriever` wrapping `CohereRerank`, `CrossEncoderReranker`, or `FlashrankRerank`. Note: `LLMChainExtractor` inside compression is extraction, not reranking — it doesn't satisfy R004 by itself.
- Filters [R005]: `search_kwargs={"filter": ...}` or store-specific filter params. Metadata exists on chunks but no filter anywhere → FINDING.
- Multi-turn [R006]: PASS signals are `create_history_aware_retriever(...)`, a condense-question step (standalone-question prompt), or legacy `ConversationalRetrievalChain` (it condenses internally). A chat app that embeds the latest user message directly → FINDING.
- Bonus context (report as inventory notes, not rules): `MultiQueryRetriever`, `ParentDocumentRetriever`, `SelfQueryRetriever` — each changes how C/R rules should be read (e.g., ParentDocumentRetriever means retrieval-chunk size ≠ context-chunk size).

## Prompt & Generation [P001–P006]

Find the prompt: `ChatPromptTemplate.from_messages([...])`, `PromptTemplate(...)`, or `hub.pull("...")`. For `hub.pull`, fetch/read the actual prompt text if possible — the popular `rlm/rag-prompt` already contains a don't-know instruction, which changes P003's verdict.

- Context assembly: `create_stuff_documents_chain(llm, prompt)` joins docs into `{context}`; manual LCEL often does `"\n\n".join(d.page_content for d in docs)`. Bare concatenation with no delimiters/tags around the context block → [P001].
- Read the system/template text directly for grounding wording [P002], insufficient-context handling [P003], and citation instructions [P004]. These are judged on the prompt *text*, not on which chain class is used.
- Token guard [P005]: look for `trim_messages`, manual token counting (`tiktoken`, `get_num_tokens`), or max-doc caps before assembly. `k × chunk_size` plus unbounded `ChatMessageHistory` with no trimming → FINDING.
- Ordering [P006]: docs usually flow in retriever score order (best-first), which PASSES. A FINDING needs evidence of shuffling/reversing, or long contexts where known-best chunks land mid-sequence.
- Legacy `RetrievalQA(chain_type=...)`: `"stuff"` is the common case (audit the stuff prompt); `map_reduce`/`refine` change P005/P006 dynamics — note it in the inventory.

## Observability [O001–O004]

- LangSmith: env vars `LANGSMITH_TRACING` / `LANGCHAIN_TRACING_V2`, `LANGSMITH_API_KEY`. When tracing is on and retrieval runs *inside* the chain/graph, retriever spans (chunks + scores) are captured automatically → O001/O002 PASS.
- Langfuse: `CallbackHandler` from the langfuse SDK passed via `config={"callbacks": [...]}`, or `@observe` decorators. Same span logic applies.
- OpenTelemetry: manual spans around retrieval/generation — verify the retrieval span actually records document IDs/scores, not just timing [O001].
- Common FINDING pattern: tracing initialized, but a code path calls `llm.invoke(...)` directly with hand-built strings, bypassing the traced retriever — chunks never reach the trace [O001].
- Feedback [O003]: any score/feedback API call (`langfuse.score(...)`, LangSmith feedback) wired to a UI signal. Absence → FINDING.

## LangGraph notes

In LangGraph apps, stages live in graph nodes: find the retrieval node (calls a retriever, writes docs into state) and the generation node (reads state docs into the prompt). Audit the same rules against node internals. Query rewriting [R006] appears as a dedicated node or a router; its absence in a chat graph is still a FINDING. State-held chat history without trimming feeds [P005].

## Known deviations to expect

- Config split between `.env` / YAML and code — read both before marking UNKNOWN.
- JS projects mirror the Python APIs with camelCase (`chunkOverlap`, `searchKwargs`); the same checks apply.
- Wrappers: teams often wrap LangChain in their own `RagService` class — audit the wrapper's call sites, not just top-level scripts.
