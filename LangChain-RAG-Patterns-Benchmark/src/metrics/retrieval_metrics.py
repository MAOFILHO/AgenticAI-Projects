"""Custom retrieval metrics: Hit Rate, MRR, Precision@K, Recall@K, nDCG@K.

Pure-Python implementations -- no evaluation framework dependency. Relevance
is determined by word-overlap
between a retrieved chunk and the question's `gold_context` passage.
"""
import numpy as np

from src import config


def is_relevant(retrieved_text, gold_context, threshold=None):
    """Check if a retrieved chunk is relevant via word overlap with gold context."""
    threshold = config.RELEVANCE_THRESHOLD if threshold is None else threshold
    gold_words = set(gold_context.lower().split())
    retrieved_words = set(retrieved_text.lower().split())
    if not gold_words:
        return False
    overlap = len(gold_words & retrieved_words) / len(gold_words)
    return overlap >= threshold


def hit_rate_at_k(retrieved_docs_list, gold_contexts, k):
    """Hit Rate@K: fraction of queries with at least one relevant doc in top-K."""
    if not gold_contexts:
        return 0.0
    hits = 0
    for docs, gold in zip(retrieved_docs_list, gold_contexts):
        if any(is_relevant(d.page_content, gold) for d in docs[:k]):
            hits += 1
    return hits / len(gold_contexts)


def mrr_at_k(retrieved_docs_list, gold_contexts, k):
    """Mean Reciprocal Rank@K: average of 1/rank of first relevant doc."""
    rrs = []
    for docs, gold in zip(retrieved_docs_list, gold_contexts):
        rr = 0.0
        for rank, d in enumerate(docs[:k], start=1):
            if is_relevant(d.page_content, gold):
                rr = 1.0 / rank
                break
        rrs.append(rr)
    return float(np.mean(rrs)) if rrs else 0.0


def precision_at_k(retrieved_docs_list, gold_contexts, k):
    """Precision@K: fraction of top-K retrieved docs that are relevant."""
    precisions = []
    for docs, gold in zip(retrieved_docs_list, gold_contexts):
        top_k = docs[:k]
        if not top_k:
            precisions.append(0.0)
            continue
        relevant = sum(1 for d in top_k if is_relevant(d.page_content, gold))
        precisions.append(relevant / len(top_k))
    return float(np.mean(precisions)) if precisions else 0.0


def recall_at_k(retrieved_docs_list, gold_contexts, k):
    """Recall@K: fraction of queries where the gold context was retrieved (single relevant doc per query)."""
    recalls = []
    for docs, gold in zip(retrieved_docs_list, gold_contexts):
        relevant_in_topk = sum(1 for d in docs[:k] if is_relevant(d.page_content, gold))
        # Each query has exactly one gold_context passage to find.
        recalls.append(min(relevant_in_topk, 1) / 1.0)
    return float(np.mean(recalls)) if recalls else 0.0


def ndcg_at_k(retrieved_docs_list, gold_contexts, k):
    """nDCG@K: are relevant docs ranked highest? (binary relevance).

    IDCG is computed from the actual number of relevant chunks retrieved in the
    top-K (placed at the top ranks in the ideal ordering), so nDCG stays in [0, 1]
    even when a query has more than one relevant chunk.
    """
    ndcgs = []
    for docs, gold in zip(retrieved_docs_list, gold_contexts):
        relevance = [1 if is_relevant(d.page_content, gold) else 0 for d in docs[:k]]
        dcg = sum(rel / np.log2(rank + 1) for rank, rel in enumerate(relevance, start=1))

        num_relevant = sum(relevance)
        idcg = sum(1.0 / np.log2(rank + 1) for rank in range(1, num_relevant + 1))

        ndcgs.append(dcg / idcg if idcg > 0 else 0.0)
    return float(np.mean(ndcgs)) if ndcgs else 0.0


def compute_retrieval_metrics(retrieved_docs_list, gold_contexts, k=None):
    """Compute all five retrieval metrics at once. Returns a dict."""
    k = k or config.TOP_K
    return {
        f"Hit Rate@{k}": hit_rate_at_k(retrieved_docs_list, gold_contexts, k),
        f"MRR@{k}": mrr_at_k(retrieved_docs_list, gold_contexts, k),
        f"Precision@{k}": precision_at_k(retrieved_docs_list, gold_contexts, k),
        f"Recall@{k}": recall_at_k(retrieved_docs_list, gold_contexts, k),
        f"nDCG@{k}": ndcg_at_k(retrieved_docs_list, gold_contexts, k),
    }
