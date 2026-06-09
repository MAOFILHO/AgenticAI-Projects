#!/usr/bin/env python3
"""
MidwestBank AML Compliance Pipeline — 5-ADK Comparison
=======================================================
Runs the same BSA/AML compliance reporting pipeline using five different
agentic AI frameworks and shows a side-by-side comparison at the end.

Frameworks:
  1. LangGraph       — graph-based, explicit nodes/edges, fan-out workers
  2. OpenAI Agent SDK — handoff-based, triage + specialist agents
  3. CrewAI          — role-based sequential (Researcher → Analyst → Writer)
  4. AutoGen         — group chat, RoundRobin conversation
  5. Google ADK      — Parallel + Sequential + Loop agent pipeline

Usage:
  python main.py                    # run all 5
  python main.py --only langgraph   # run one framework
  python main.py --skip google_adk  # skip one framework
"""
import argparse
import os
import sys
import traceback

from dotenv import load_dotenv

# Load .env before any framework imports
load_dotenv()

if "OPENAI_API_KEY" not in os.environ:
    print("ERROR: OPENAI_API_KEY not set. Copy .env.example to .env and add your key.")
    sys.exit(1)

# ── LangSmith tracing ────────────────────────────────────────────────────────
# Enabled automatically when LANGCHAIN_API_KEY is present in .env.
# LangGraph is traced natively; the other 4 frameworks use @traceable wrappers.
_langsmith_enabled = bool(os.getenv("LANGCHAIN_API_KEY"))
if _langsmith_enabled:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", os.getenv("LANGCHAIN_PROJECT", "compare-adks"))

# ── Suppress CrewAI's interactive trace prompt ───────────────────────────────
# CrewAI has its own platform (crew.ai), separate from LangSmith. It asks once
# on first run. We disable it here so main.py runs non-interactively.
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

from shared.data_loader import get_stats, load_data
from shared.metrics import RunMetrics
from comparison.report import print_comparison

RUNNERS = [
    ("langgraph",      "LangGraph",       "runners.langgraph_runner"),
    ("openai_agents",  "OpenAI Agent SDK","runners.openai_agents_runner"),
    ("crewai",         "CrewAI",          "runners.crewai_runner"),
    ("autogen",        "AutoGen",         "runners.autogen_runner"),
    ("google_adk",     "Google ADK",      "runners.google_adk_runner"),
]


def print_header():
    print("\n" + "=" * 70)
    print("  MIDWESTBANK AML COMPLIANCE PIPELINE — 5-ADK COMPARISON")
    print("=" * 70)
    print("  Business Case: MidwestBank BSA/AML Compliance Reporting")
    print("  Dataset:       customers.csv, transactions.csv, sar_filings.csv,")
    print("                 prior_findings.csv, regulatory_thresholds.json")
    tracing_status = (
        f"enabled  → project: {os.getenv('LANGCHAIN_PROJECT', 'compare-adks')}"
        if _langsmith_enabled else "disabled (set LANGCHAIN_API_KEY in .env to enable)"
    )
    print(f"  LangSmith:     {tracing_status}")
    print("=" * 70)


def print_dataset_summary():
    print("\n  Loading dataset...")
    stats = get_stats()
    print(f"\n  Dataset Summary:")
    print(f"    Customers         : {stats['total_customers']:,}")
    print(f"    Transactions      : {stats['total_transactions']:,}")
    print(f"    Suspicious txns   : {stats['suspicious_count']:,} ({stats['suspicious_pct']}%)")
    print(f"    SAR filings       : {stats['sar_total']:,}")
    print(f"    KYC verified      : {stats['kyc_verified_pct']}%")
    print(f"    PEP customers     : {stats['pep_count']}")
    print()


def run_framework(key: str, name: str, module_path: str) -> tuple[RunMetrics, str]:
    import importlib
    metrics = RunMetrics(framework=name)
    try:
        module = importlib.import_module(module_path)
        if _langsmith_enabled:
            from langsmith import traceable
            traced_run = traceable(
                name=f"[{name}] compliance_pipeline",
                run_type="chain",
                tags=["compare-adks", key],
            )(module.run)
            report = traced_run(metrics)
        else:
            report = module.run(metrics)
        metrics.finish(report)
    except Exception as e:
        metrics.fail(str(e))
        report = f"ERROR: {e}"
        print(f"\n[{name}] ERROR: {e}")
        traceback.print_exc()
    return metrics, report


def main():
    parser = argparse.ArgumentParser(description="Compare 5 ADK frameworks on the same compliance pipeline")
    parser.add_argument("--only", choices=[r[0] for r in RUNNERS], help="Run only one framework")
    parser.add_argument("--skip", choices=[r[0] for r in RUNNERS], help="Skip one framework")
    args = parser.parse_args()

    print_header()
    print_dataset_summary()

    active_runners = RUNNERS
    if args.only:
        active_runners = [r for r in RUNNERS if r[0] == args.only]
    elif args.skip:
        active_runners = [r for r in RUNNERS if r[0] != args.skip]

    print(f"  Running {len(active_runners)} framework(s): {', '.join(r[1] for r in active_runners)}")

    results: list[tuple[RunMetrics, str]] = []

    for key, name, module_path in active_runners:
        metrics, report = run_framework(key, name, module_path)
        results.append((metrics, report))
        status_icon = "✓" if metrics.status == "success" else "✗"
        print(f"\n  {status_icon} {name} completed in {metrics.elapsed_seconds}s")

    if len(results) > 1:
        print_comparison(results)
    elif len(results) == 1:
        m, r = results[0]
        print(f"\n[{m.framework}] Status: {m.status} | Time: {m.elapsed_seconds}s | Words: {m.report_word_count}")

    if _langsmith_enabled:
        project = os.getenv("LANGCHAIN_PROJECT", "compare-adks")
        print(f"\n  LangSmith traces → https://smith.langchain.com/projects/{project}")


if __name__ == "__main__":
    main()
