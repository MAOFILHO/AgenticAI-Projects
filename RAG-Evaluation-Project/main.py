#!/usr/bin/env python3
"""RAG Pattern Comparison & Evaluation Pipeline.

Runs the RAG evaluation framework (custom retrieval metrics:
Hit Rate, MRR, Precision@K, Recall@K, nDCG@K; LLM-as-judge generation
metrics: Answer Relevance, Groundedness, Hallucination Rate, Coherence;
RAGAS metrics) against the same 40-question evaluation dataset
and document corpus, once per RAG pattern:

  1. FAISS Similarity Search
  2. FAISS MMR (Diversity)
  3. ChromaDB Similarity Search
  4. ChromaDB MMR (Diversity)
  5. Agentic RAG (ReAct + Iterative)
  6. OpenAI File Search (Hosted VS)

At the end, prints a side-by-side comparison and exports a multi-sheet
Excel report to outputs/.

Additionally, a 7th pattern -- Multimodal Vision + Text RAG (SecureLife) --
runs as a separate demo (3 damage photos -> coverage decisions), since its
inputs/outputs don't fit the text retrieval/generation metrics used by
patterns 1-6. Skip it with --no-multimodal.

Usage:
    python main.py                  # run all patterns
    python main.py --patterns 1 3   # run only patterns 1 and 3 (1-indexed)
    python main.py --quick          # E2E_SAMPLE_SIZE=2 (fast smoke run)
    python main.py --no-multimodal  # skip the multimodal demo
"""
import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from src import config, data_loader, report
from src.evaluator import evaluate_pattern
from src.patterns import get_all_patterns


def check_api_key():
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set. Copy .env.example to .env and add your key.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Run the RAG pattern comparison & evaluation pipeline.")
    parser.add_argument(
        "--patterns",
        nargs="+",
        type=int,
        default=None,
        help="1-indexed list of patterns to run (default: all 6).",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Smoke-test mode: evaluate only 2 sample questions for generation metrics.",
    )
    parser.add_argument(
        "--no-multimodal",
        action="store_true",
        help="Skip the Multimodal Vision + Text RAG (SecureLife) demo.",
    )
    args = parser.parse_args()

    if args.quick:
        config.E2E_SAMPLE_SIZE = 2

    check_api_key()

    print("=" * 70)
    print("  RAG PATTERN COMPARISON & EVALUATION PIPELINE")
    print(f"  Evaluation framework: retrieval metrics + LLM-as-judge")
    print("=" * 70)

    if config.TRACING_ENABLED:
        print(f"\nLangSmith tracing ENABLED (project: '{config.LANGSMITH_PROJECT}')")
        print(f"  View traces at: {config.langsmith_project_url()}")
    else:
        print("\nLangSmith tracing DISABLED (set LANGSMITH_API_KEY in .env to enable).")

    if config.LANGFUSE_TRACING_ENABLED:
        print("\nLangfuse tracing ENABLED (covers all 7 patterns, including the raw")
        print("  OpenAI SDK File Search pattern that LangSmith cannot trace).")
        print(f"  View traces at: {config.langfuse_project_url()}")
    else:
        print("\nLangfuse tracing DISABLED (set LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY")
        print("  in .env to enable -- this is the only tracer that covers the raw")
        print("  OpenAI SDK File Search pattern).")

    print("\nLoading evaluation dataset and document corpus...")
    eval_dataset = data_loader.load_eval_dataset()
    corpus = data_loader.load_corpus()
    print(f"  Eval dataset: {len(eval_dataset)} questions")
    print(f"  Corpus: {len(corpus)} chunks/documents")

    all_patterns = get_all_patterns()
    if args.patterns:
        selected = [all_patterns[i - 1] for i in args.patterns if 1 <= i <= len(all_patterns)]
    else:
        selected = all_patterns

    all_results = []
    for pattern in selected:
        try:
            result = evaluate_pattern(pattern, corpus, eval_dataset)
            all_results.append(result)
        except Exception as e:
            print(f"\n  ERROR running {pattern.name}: {e}")
            try:
                pattern.cleanup()
            except Exception:
                pass

    if not all_results:
        print("\nNo patterns completed successfully. Exiting.")
        sys.exit(1)

    report.print_comparison(all_results)
    report.export_to_excel(all_results)
    report.export_to_json(all_results)

    if not args.no_multimodal:
        from src.patterns import multimodal_securelife

        try:
            multimodal_securelife.run_demo()
        except Exception as e:
            print(f"\n  ERROR running {multimodal_securelife.PATTERN_NAME}: {e}")


if __name__ == "__main__":
    main()
