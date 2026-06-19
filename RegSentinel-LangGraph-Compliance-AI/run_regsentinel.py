#!/usr/bin/env python3
"""RegSentinel — CLI entrypoint.

Usage:
    python run_regsentinel.py              # full pipeline (Q3 2026 report)
    python run_regsentinel.py --eval       # also run evaluation metrics
    python run_regsentinel.py --cip        # also run multimodal CIP (Task 5 stretch)
    python run_regsentinel.py --eval --cip # all tasks
"""
import argparse
import sys

# ── Config must load first (validates keys + paths) ───────────────────────────
from src.config import OPENAI_MODEL  # noqa: F401 (triggers validation)

from src.data_loader import print_data_summary
from src.graph import get_app
from src.observability import setup_observability
from src.pii_redaction import redact_pii
from src.rag import get_vectorstore


def run_pipeline(thread_id: str = "Q3_2026_Compliance_Run") -> dict:
    """Execute the full compliance pipeline and return the final state."""
    app = get_app()
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {
        "user_request": "Execute complete Q3 2026 framework compliance assessment and synthesize report.",
        "revision_count": 0,
        "findings": [],
        "guardrail_alerts": [],
    }
    print("\n🚀 Launching RegSentinel compliance pipeline...")
    state = app.invoke(inputs, config)
    print("🏁 Pipeline finished.")
    return state


def display_report(state: dict) -> None:
    raw = state.get("final_report", "")
    redacted = redact_pii(raw)

    print("\n" + "=" * 72)
    print("FINAL COMPLIANCE REPORT (PII-redacted)")
    print("=" * 72)
    print(f"revisions run : {state.get('revision_count', '—')}")
    print(f"quality passed: {state.get('quality_passed', '—')}")
    print(f"findings merged (reducer): {len(state.get('findings', []))}")
    print(f"guardrail alerts         : {len(state.get('guardrail_alerts', []))}")
    print("=" * 72)
    print(redacted)


def run_evaluation(state: dict) -> None:
    from src.evaluation import citation_accuracy, judge_report

    report = state.get("final_report", "")
    print("\n" + "=" * 60)
    print("🎯 EVALUATION METRICS")
    print("=" * 60)
    cit = citation_accuracy(report)
    print(f"citation_accuracy : score={cit['score']}  n_citations={cit['n_citations']}")
    if cit["hallucinated_ids"]:
        print(f"  hallucinated IDs: {cit['hallucinated_ids']}")
    judge = judge_report(report)
    print(f"llm_judge         : faithfulness={judge['faithfulness']}  completeness={judge['completeness']}")
    print(f"  notes: {judge['notes']}")
    print("=" * 60)


def run_cip() -> None:
    from src.cip_multimodal import (
        cip_extract_from_image,
        img_to_b64,
        make_fake_registration,
        verify_cip,
    )

    print("\n" + "=" * 60)
    print("🪪 MULTIMODAL CIP VERIFICATION (Task 5)")
    print("=" * 60)
    scan = make_fake_registration(name="Coastal Imports LLC", ein="12-3456789")
    b64 = img_to_b64(scan)
    extracted = cip_extract_from_image(b64)
    print("Extracted CIP fields:")
    print(extracted)

    # Simple ledger for cross-check
    ledger = {"CUST-001": {"name": "Coastal Imports LLC", "ein": "12-3456789"}}
    result = verify_cip("CUST-001", extracted, ledger)
    print(f"\nCIP verification: {result}")


def main() -> None:
    parser = argparse.ArgumentParser(description="RegSentinel Compliance Pipeline")
    parser.add_argument("--eval", action="store_true", help="Run evaluation metrics after pipeline")
    parser.add_argument("--cip",  action="store_true", help="Run multimodal CIP verification (stretch)")
    args = parser.parse_args()

    # Task 3: boot observability (no-op if key absent)
    setup_observability()

    # Data summary
    print_data_summary()

    # Boot RAG (builds Chroma vector store)
    get_vectorstore()

    # Core pipeline
    state = run_pipeline()
    display_report(state)

    # Optional tasks
    if args.eval:
        run_evaluation(state)

    if args.cip:
        run_cip()

    print("\n✅ RegSentinel run complete.")


if __name__ == "__main__":
    main()
