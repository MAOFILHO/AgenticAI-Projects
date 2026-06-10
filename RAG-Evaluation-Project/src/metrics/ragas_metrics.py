"""RAGAS metrics: Faithfulness, Answer Relevancy, Context Precision, Context Recall.

Enabled by default
(ENABLE_RAGAS=true in .env.example) -- ragas + datasets are part of
requirements.txt, along with a compatibility shim
(scripts/patch_ragas_vertexai_shim.py) for ragas' import of the now-removed
langchain_community.chat_models.vertexai module.

Set ENABLE_RAGAS=false in .env to skip these metrics (fewer LLM calls). If
`ragas` isn't installed, `is_available()` returns False and the pipeline
skips this section entirely (logged, not an error).
"""
from src import config


def is_available():
    if not config.ENABLE_RAGAS:
        return False
    try:
        import ragas  # noqa: F401
        import datasets  # noqa: F401
    except ImportError:
        return False
    return True


def compute_ragas_metrics(questions, answers, contexts_list, ground_truths):
    """Run RAGAS evaluation. Returns a dict of metric_name -> average score."""
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

    ragas_dataset = Dataset.from_dict(
        {
            "question": questions,
            "answer": answers,
            "contexts": contexts_list,
            "ground_truth": ground_truths,
        }
    )

    results = evaluate(
        dataset=ragas_dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )
    df = results.to_pandas()

    return {
        "Faithfulness": float(df["faithfulness"].mean()) if "faithfulness" in df else 0.0,
        "Answer Relevancy": float(df["answer_relevancy"].mean()) if "answer_relevancy" in df else 0.0,
        "Context Precision": float(df["context_precision"].mean()) if "context_precision" in df else 0.0,
        "Context Recall": float(df["context_recall"].mean()) if "context_recall" in df else 0.0,
    }
