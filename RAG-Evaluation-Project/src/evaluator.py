"""Run the evaluation pipeline for a single RAG pattern."""
import time

from langchain_openai import ChatOpenAI

from src import config
from src.metrics import ragas_metrics
from src.metrics.generation_metrics import aggregate_generation_metrics, evaluate_answer
from src.metrics.retrieval_metrics import compute_retrieval_metrics


def evaluate_pattern(pattern, corpus, eval_dataset, verbose=True):
    """Build `pattern`, run it over `eval_dataset`, and return a results dict.

    - Retrieval metrics are computed over the FULL eval_dataset (cheap, no LLM calls).
    - Generation (LLM-as-judge) and RAGAS metrics run on a sample of
      config.E2E_SAMPLE_SIZE questions to control cost/runtime.
    """
    if verbose:
        print(f"\n{'=' * 70}")
        print(f"  Now running the RAG Evaluation pipeline using: {pattern.name}")
        print(f"  {pattern.description}")
        print(f"{'=' * 70}")

    start = time.time()
    pattern.build(corpus)
    build_time = time.time() - start
    if verbose:
        print(f"  Index/agent built in {build_time:.1f}s")

    # --- Retrieval metrics over the full dataset ---
    all_retrieved = []
    all_gold_contexts = []
    all_questions = []
    if verbose:
        print(f"  Retrieving top-{config.TOP_K} chunks for {len(eval_dataset)} questions...")

    for item in eval_dataset:
        retrieved = pattern.retrieve(item["question"])
        all_retrieved.append(retrieved)
        all_gold_contexts.append(item["gold_context"])
        all_questions.append(item["question"])

    retrieval_metrics = compute_retrieval_metrics(all_retrieved, all_gold_contexts)
    if verbose:
        print(f"  Retrieval metrics (K={config.TOP_K}):")
        for name, value in retrieval_metrics.items():
            print(f"    {name:<14s} {value:.4f}")

    # --- Generation (LLM-as-judge) metrics on a sample ---
    sample = eval_dataset[: config.E2E_SAMPLE_SIZE]
    judge_llm = ChatOpenAI(model=config.JUDGE_LLM, temperature=config.JUDGE_TEMPERATURE)

    if verbose:
        print(f"  Running end-to-end (LLM-as-judge) evaluation on {len(sample)} sample questions...")

    per_query_results = []
    sample_answers = []
    sample_contexts = []
    for i, item in enumerate(sample):
        retrieved, answer = pattern.run(item["question"])
        context = "\n\n".join(d.page_content for d in retrieved)
        scores = evaluate_answer(item["question"], context, answer, judge_llm)
        scores["question_id"] = item["question_id"]
        per_query_results.append(scores)
        sample_answers.append(answer)
        sample_contexts.append([d.page_content for d in retrieved] or [""])
        if verbose:
            print(f"    [{i + 1}/{len(sample)}] {item['question_id']}: {answer[:80]}...")

    generation_metrics = aggregate_generation_metrics(per_query_results)
    if verbose:
        print("  Generation metrics:")
        for name, value in generation_metrics.items():
            print(f"    {name:<26s} {value:.4f}")

    # --- Optional RAGAS metrics on the same sample ---
    ragas_scores = None
    if ragas_metrics.is_available():
        if verbose:
            print("  Running RAGAS metrics (faithfulness, relevancy, precision, recall)...")
        ragas_scores = ragas_metrics.compute_ragas_metrics(
            questions=[item["question"] for item in sample],
            answers=sample_answers,
            contexts_list=sample_contexts,
            ground_truths=[item["ground_truth"] for item in sample],
        )
        if verbose:
            for name, value in ragas_scores.items():
                print(f"    {name:<20s} {value:.4f}")
    elif verbose and config.ENABLE_RAGAS:
        print("  RAGAS enabled but not installed -- skipping (see requirements-ragas.txt).")

    pattern.cleanup()
    total_time = time.time() - start

    return {
        "pattern": pattern.name,
        "description": pattern.description,
        "build_time_sec": build_time,
        "total_time_sec": total_time,
        "retrieval_metrics": retrieval_metrics,
        "generation_metrics": generation_metrics,
        "ragas_metrics": ragas_scores,
        "per_query_generation": per_query_results,
        "sample_size": len(sample),
        "dataset_size": len(eval_dataset),
    }
