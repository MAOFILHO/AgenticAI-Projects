"""RAG retrieval quality tests."""

import pytest

from tests.conftest import requires_openai


@requires_openai
def test_return_policy_retrieval(data):
    from shopsmart.config import build_embeddings
    from shopsmart.rag import build_policy_retriever

    retriever = build_policy_retriever(data["policies_text"], build_embeddings())
    results = retriever.invoke("What is the return policy?")
    assert len(results) == 3
    combined = " ".join(doc.page_content.lower() for doc in results)
    assert "return" in combined


@requires_openai
def test_shipping_policy_retrieval(data):
    from shopsmart.config import build_embeddings
    from shopsmart.rag import build_policy_retriever

    retriever = build_policy_retriever(data["policies_text"], build_embeddings())
    results = retriever.invoke("How long does shipping take?")
    assert len(results) == 3
    combined = " ".join(doc.page_content.lower() for doc in results)
    assert "ship" in combined or "deliver" in combined


@requires_openai
def test_escalation_policy_retrieval(data):
    from shopsmart.config import build_embeddings
    from shopsmart.rag import build_policy_retriever

    retriever = build_policy_retriever(data["policies_text"], build_embeddings())
    results = retriever.invoke("When should a ticket be escalated?")
    assert len(results) == 3
    combined = " ".join(doc.page_content.lower() for doc in results)
    assert "escalat" in combined or "manager" in combined
