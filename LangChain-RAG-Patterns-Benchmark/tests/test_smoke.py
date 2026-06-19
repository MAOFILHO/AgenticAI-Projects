"""Smoke tests that don't call the OpenAI API.

Covers: dataset/corpus loading, retrieval metric functions, pattern
instantiation, and report formatting against synthetic data. A dummy
OPENAI_API_KEY is sufficient (client objects are constructed but never
called) -- no real key or network access is required.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("OPENAI_API_KEY", "sk-smoke-test-dummy")

from src import config, data_loader
from src.metrics.retrieval_metrics import compute_retrieval_metrics, is_relevant
from src.patterns.base import RetrievedChunk
from src.patterns import get_all_patterns
from src.patterns import multimodal_securelife
from src import report


def test_load_eval_dataset():
    dataset = data_loader.load_eval_dataset()
    assert len(dataset) == 40
    item = dataset[0]
    for key in ("question_id", "question", "ground_truth", "gold_context", "source_document"):
        assert key in item


def test_load_corpus():
    corpus = data_loader.load_corpus()
    assert len(corpus) > 0
    assert all(hasattr(d, "page_content") for d in corpus)


def test_is_relevant():
    gold = "the transformer is based solely on attention mechanisms"
    relevant_text = "The Transformer architecture is based solely on attention mechanisms and dispenses with recurrence."
    irrelevant_text = "Bananas are a good source of potassium and grow in tropical climates."
    assert is_relevant(relevant_text, gold) is True
    assert is_relevant(irrelevant_text, gold) is False


def test_retrieval_metrics_synthetic():
    gold_contexts = ["the transformer uses attention mechanisms", "resnet uses residual connections"]
    retrieved_docs_list = [
        [RetrievedChunk(page_content="the transformer uses attention mechanisms heavily")],
        [RetrievedChunk(page_content="completely unrelated text about cooking recipes")],
    ]
    metrics = compute_retrieval_metrics(retrieved_docs_list, gold_contexts, k=1)
    assert metrics[f"Hit Rate@1"] == 0.5
    assert 0.0 <= metrics[f"MRR@1"] <= 1.0
    assert 0.0 <= metrics[f"nDCG@1"] <= 1.0


def test_get_all_patterns():
    patterns = get_all_patterns()
    assert len(patterns) == 6
    names = [p.name for p in patterns]
    assert len(set(names)) == 6  # all unique


def test_multimodal_securelife_setup():
    # Claim record + sample images load from disk; vector store/graph construct
    # client objects but make no API calls.
    claim = multimodal_securelife.load_claim()
    assert claim["claim_id"] == multimodal_securelife.DEFAULT_CLAIM_ID
    assert claim["claim_amount"] > 0

    images = multimodal_securelife.load_sample_images()
    assert set(images.keys()) == set(multimodal_securelife.SAMPLE_IMAGE_FILES.keys())
    assert all(len(b) > 0 for b in images.values())

    agent = multimodal_securelife.build_graph(_FakeVectorstore())
    assert agent is not None


class _FakeVectorstore:
    """Stand-in for FAISS so build_graph() can be smoke-tested without embeddings."""

    def similarity_search(self, query, k=2):
        return []


def test_report_print_comparison_synthetic(capsys):
    fake_result = {
        "pattern": "Fake Pattern",
        "description": "test",
        "build_time_sec": 1.0,
        "total_time_sec": 2.0,
        "retrieval_metrics": compute_retrieval_metrics(
            [[RetrievedChunk(page_content="x")]], ["x"], k=config.TOP_K
        ),
        "generation_metrics": {
            "Answer Relevance (1-5)": 4.0,
            "Groundedness (1-5)": 4.0,
            "Hallucination Rate (0-1)": 0.1,
            "Coherence (1-5)": 4.0,
        },
        "ragas_metrics": None,
        "per_query_generation": [],
        "sample_size": 1,
        "dataset_size": 1,
    }
    report.print_comparison([fake_result, fake_result])
    captured = capsys.readouterr()
    assert "RAG PATTERN COMPARISON" in captured.out
    assert "Fake Pattern" in captured.out


if __name__ == "__main__":
    test_load_eval_dataset()
    print("test_load_eval_dataset: OK")
    test_load_corpus()
    print("test_load_corpus: OK")
    test_is_relevant()
    print("test_is_relevant: OK")
    test_retrieval_metrics_synthetic()
    print("test_retrieval_metrics_synthetic: OK")
    test_get_all_patterns()
    print("test_get_all_patterns: OK")
    test_multimodal_securelife_setup()
    print("test_multimodal_securelife_setup: OK")
    print("\nAll smoke tests passed (no API key required).")
