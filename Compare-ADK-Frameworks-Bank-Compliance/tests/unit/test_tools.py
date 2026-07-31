"""Tests for shared/tools.py — the business logic every runner wraps.

These functions are the contract between the dataset and all six frameworks, so
their output shape matters more than any single framework's plumbing.
"""
from __future__ import annotations

import json

import pytest

from shared.tools import (
    detect_aml_patterns,
    get_kyc_stats,
    get_risk_summary,
    get_sar_status,
    get_transaction_stats,
)

ALL_TOOLS = [
    get_transaction_stats,
    get_sar_status,
    get_kyc_stats,
    detect_aml_patterns,
    get_risk_summary,
]


@pytest.mark.parametrize("tool", ALL_TOOLS, ids=lambda f: f.__name__)
def test_tool_returns_valid_json_string(clear_data_cache, tool):
    out = tool()
    assert isinstance(out, str)
    parsed = json.loads(out)  # must not raise
    assert isinstance(parsed, dict)
    assert parsed, f"{tool.__name__} returned an empty object"


@pytest.mark.parametrize("tool", ALL_TOOLS, ids=lambda f: f.__name__)
def test_tool_has_docstring(tool):
    """Docstrings become the tool description the LLM sees — they must exist."""
    assert tool.__doc__ and tool.__doc__.strip()


def test_transaction_stats_shape(clear_data_cache):
    d = json.loads(get_transaction_stats())
    for key in (
        "total_transactions", "total_amount_usd", "suspicious_transactions",
        "suspicious_percentage", "suspicious_total_amount_usd",
        "ctr_eligible_over_10k", "ctr_threshold_usd",
    ):
        assert key in d
    assert d["total_transactions"] > 0
    assert d["suspicious_transactions"] <= d["total_transactions"]
    assert 0 <= d["suspicious_percentage"] <= 100


def test_sar_status_shape(clear_data_cache):
    d = json.loads(get_sar_status())
    for key in ("total_sar_filings", "sar_by_status", "sar_by_type", "total_amount_involved_usd"):
        assert key in d
    assert isinstance(d["sar_by_status"], dict)
    assert isinstance(d["sar_by_type"], dict)
    assert sum(d["sar_by_status"].values()) == d["total_sar_filings"]


def test_kyc_stats_shape(clear_data_cache):
    d = json.loads(get_kyc_stats())
    for key in (
        "total_customers", "kyc_verified", "kyc_verified_pct", "kyc_expired",
        "kyc_pending", "pep_flagged_customers", "risk_score_distribution",
    ):
        assert key in d
    assert d["kyc_verified"] + d["kyc_expired"] + d["kyc_pending"] <= d["total_customers"]
    assert 0 <= d["kyc_verified_pct"] <= 100


def test_aml_patterns_shape(clear_data_cache):
    d = json.loads(detect_aml_patterns())
    for key in (
        "aml_patterns_detected", "patterns",
        "total_suspicious_transactions", "requires_sar_filing",
    ):
        assert key in d
    assert isinstance(d["patterns"], list)
    assert d["aml_patterns_detected"] == len(d["patterns"])
    assert isinstance(d["requires_sar_filing"], bool)
    for pattern in d["patterns"]:
        assert {"pattern", "count", "description"} <= set(pattern)


def test_risk_summary_shape(clear_data_cache):
    d = json.loads(get_risk_summary())
    for key in (
        "high_risk_customers", "pep_customers",
        "kyc_deficiencies", "pending_sar_filings", "priority_actions",
    ):
        assert key in d
    assert isinstance(d["priority_actions"], list)
    assert len(d["priority_actions"]) == 4
    assert all(isinstance(a, str) and a.strip() for a in d["priority_actions"])


def test_tools_are_consistent_with_each_other(clear_data_cache):
    """A compliance report is wrong if two sections cite different totals for the
    same fact — that is literally one of the pain points this project targets."""
    txn = json.loads(get_transaction_stats())
    patterns = json.loads(detect_aml_patterns())
    kyc = json.loads(get_kyc_stats())
    risk = json.loads(get_risk_summary())

    assert txn["suspicious_transactions"] == patterns["total_suspicious_transactions"]
    assert kyc["pep_flagged_customers"] == risk["pep_customers"]
    assert kyc["kyc_expired"] + kyc["kyc_pending"] == risk["kyc_deficiencies"]


def test_tools_are_deterministic(clear_data_cache):
    """Same dataset in, same JSON out — required for the frameworks to be comparable."""
    for tool in ALL_TOOLS:
        assert tool() == tool()
