"""Fixture for RAG-R008: raw BM25 and vector scores are added directly."""


def merge_results(bm25_results, vector_results):
    by_id = {}

    for doc_id, score in bm25_results:
        by_id.setdefault(doc_id, 0.0)
        by_id[doc_id] += score

    for doc_id, score in vector_results:
        by_id.setdefault(doc_id, 0.0)
        by_id[doc_id] += score

    return sorted(by_id.items(), key=lambda item: item[1], reverse=True)


if __name__ == "__main__":
    merged = merge_results([("policy", 13.2)], [("faq", 0.91)])
    assert merged[0][0] == "policy"
