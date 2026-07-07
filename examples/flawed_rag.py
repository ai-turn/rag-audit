"""Test fixture: a deliberately flawed LangChain RAG bot over Korean docs.

Regression test for the rag-audit skill: audit this file and compare against
the two lists below. Rules not listed are judgment calls on a one-shot demo
script (C005, E003, R005, P005, O003, O004, V*) — the test is silent on them
by design, so verdict variance there does not fail the test.

MUST-FIND (each of these appears as a FINDING):
  C001 overlap=0 · C002 CharacterTextSplitter on Markdown sources ·
  C004 char-sized chunks on a Korean corpus · E001 English-only embedding
  model on Korean text · R002 no threshold / emptiness check ·
  R003 dense-only retrieval · R004 k=8 with no rerank · R007 raw question
  embedded verbatim, no query strategy · P001 bare concat prompt ·
  P002 no grounding instruction · P003 no unanswerable handling ·
  P004 metadata present but no citation instruction · O001 retrieved chunks
  not logged · O002 no tracing

MUST-NOT-FIND (never reported as a FINDING):
  C003 loader metadata preserved -> PASS · E002 same embeddings object for
  index & query -> PASS · R001 k=8 is not an extreme -> PASS · P006 chunks
  in best-first score order -> PASS · R006 single-turn by design -> N/A ·
  R008 no hybrid leg -> N/A
"""

from langchain_community.document_loaders import DirectoryLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_text_splitters import CharacterTextSplitter

EMBEDDINGS = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def build_index(docs_dir: str) -> FAISS:
    docs = DirectoryLoader(docs_dir, glob="**/*.md").load()
    splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    chunks = splitter.split_documents(docs)  # metadata preserved (C003 PASS)
    return FAISS.from_documents(chunks, EMBEDDINGS)


def answer(index: FAISS, question: str) -> str:
    docs = index.similarity_search(question, k=8)
    context = "\n".join(d.page_content for d in docs)
    prompt = context + "\n질문: " + question + "\n답변:"
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return llm.invoke(prompt).content


if __name__ == "__main__":
    idx = build_index("./docs")
    print(answer(idx, "EveryUp 에이전트의 아웃바운드 연결 방식은?"))
