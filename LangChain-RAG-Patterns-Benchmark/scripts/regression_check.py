#!/usr/bin/env python3
"""Regression test: compare the latest evaluation run against a saved baseline.

Workflow:
    python main.py --quick                  # produces outputs/latest_results.json
    python scripts/regression_check.py --save-baseline   # promote it to the baseline
    ... later, after code/prompt changes ...
    python main.py --quick
    python scripts/regression_check.py      # compares latest vs baseline, exits 1 on regression

For "higher is better" metrics (Hit Rate, MRR, Precision, Recall, nDCG,
Answer Relevance, Groundedness, Coherence, RAGAS scores), a regression is a
relative drop greater than REGRESSION_RELATIVE_DROP_THRESHOLD.

For "lower is better" metrics (Hallucination Rate), a regression is an
absolute increase greater than REGRESSION_HALLUCINATION_INCREASE_THRESHOLD.

A pattern present in the baseline but missing from the latest run (or vice
versa) is reported but does not by itself fail the check.
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import config

LOWER_IS_BETTER = {"Hallucination Rate (0-1)"}


def _load(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _check_metric_group(pattern, group_name, baseline_metrics, latest_metrics, failures):
    for metric, baseline_value in baseline_metrics.items():
        if metric not in latest_metrics:
            continue
        latest_value = latest_metrics[metric]

        if metric in LOWER_IS_BETTER:
            increase = latest_value - baseline_value
            if increase > config.REGRESSION_HALLUCINATION_INCREASE_THRESHOLD:
                failures.append(
                    f"[{pattern}] {group_name}.{metric}: {baseline_value:.4f} -> {latest_value:.4f} "
                    f"(increased by {increase:.4f}, threshold {config.REGRESSION_HALLUCINATION_INCREASE_THRESHOLD})"
                )
        else:
            if baseline_value <= 0:
                continue
            relative_drop = (baseline_value - latest_value) / baseline_value
            if relative_drop > config.REGRESSION_RELATIVE_DROP_THRESHOLD:
                failures.append(
                    f"[{pattern}] {group_name}.{metric}: {baseline_value:.4f} -> {latest_value:.4f} "
                    f"(dropped {relative_drop:.1%}, threshold {config.REGRESSION_RELATIVE_DROP_THRESHOLD:.0%})"
                )


def run_regression_check(baseline_path, latest_path):
    baseline = _load(baseline_path)
    latest = _load(latest_path)

    if latest is None:
        print(f"ERROR: latest results not found at {latest_path}. Run `python main.py` first.")
        return 1

    if baseline is None:
        print(f"No baseline found at {baseline_path}. Nothing to compare against.")
        print("Run `python scripts/regression_check.py --save-baseline` to create one.")
        return 0

    failures = []
    baseline_patterns = baseline.get("patterns", {})
    latest_patterns = latest.get("patterns", {})

    for pattern, baseline_data in baseline_patterns.items():
        if pattern not in latest_patterns:
            print(f"NOTE: pattern '{pattern}' present in baseline but missing from latest run.")
            continue
        latest_data = latest_patterns[pattern]
        _check_metric_group(
            pattern, "retrieval_metrics", baseline_data["retrieval_metrics"], latest_data["retrieval_metrics"], failures
        )
        _check_metric_group(
            pattern, "generation_metrics", baseline_data["generation_metrics"], latest_data["generation_metrics"], failures
        )
        if baseline_data.get("ragas_metrics") and latest_data.get("ragas_metrics"):
            _check_metric_group(
                pattern, "ragas_metrics", baseline_data["ragas_metrics"], latest_data["ragas_metrics"], failures
            )

    for pattern in latest_patterns:
        if pattern not in baseline_patterns:
            print(f"NOTE: pattern '{pattern}' is new in this run (not in baseline).")

    if failures:
        print(f"\nREGRESSION DETECTED ({len(failures)} metric(s) regressed):")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("No regressions detected. All metrics within thresholds of the baseline.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Compare latest RAG evaluation results against a saved baseline.")
    parser.add_argument("--baseline", default=config.BASELINE_RESULTS_PATH, help="Path to baseline JSON.")
    parser.add_argument("--latest", default=config.LATEST_RESULTS_PATH, help="Path to latest results JSON.")
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Copy the latest results to the baseline path (promotes the current run as the new baseline).",
    )
    args = parser.parse_args()

    if args.save_baseline:
        if not os.path.exists(args.latest):
            print(f"ERROR: latest results not found at {args.latest}. Run `python main.py` first.")
            sys.exit(1)
        shutil.copy(args.latest, args.baseline)
        print(f"Saved baseline: {args.baseline}")
        sys.exit(0)

    sys.exit(run_regression_check(args.baseline, args.latest))


if __name__ == "__main__":
    main()
