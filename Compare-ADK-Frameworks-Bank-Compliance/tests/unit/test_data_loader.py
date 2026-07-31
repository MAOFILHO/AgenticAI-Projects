"""Tests for shared/data_loader.py — the single source of truth all 6 runners read."""
from __future__ import annotations

import pandas as pd
import pytest

from shared import data_loader
from shared.data_loader import DATA_DIR, get_stats, load_data

EXPECTED_FILES = [
    "customers.csv",
    "transactions.csv",
    "sar_filings.csv",
    "prior_findings.csv",
    "regulatory_thresholds.json",
    "fincen_template.md",
    "occ_template.md",
    "state_template.md",
]


@pytest.mark.parametrize("filename", EXPECTED_FILES)
def test_dataset_file_exists(filename):
    assert (DATA_DIR / filename).is_file(), f"missing dataset file: {filename}"


def test_load_data_returns_all_keys(clear_data_cache):
    d = load_data()
    for key in ("customers", "transactions", "sar", "findings", "thresholds"):
        assert key in d
    for key in ("fincen_template", "occ_template", "state_template"):
        assert isinstance(d[key], str) and d[key].strip()


def test_dataframes_are_non_empty(clear_data_cache):
    d = load_data()
    for key in ("customers", "transactions", "sar", "findings"):
        assert isinstance(d[key], pd.DataFrame)
        assert len(d[key]) > 0, f"{key} dataframe is empty"


def test_load_data_is_cached(clear_data_cache):
    """Second call must return the identical object, not re-read 4MB of CSV."""
    first = load_data()
    second = load_data()
    assert first is second
    assert first["transactions"] is second["transactions"]


def test_cache_actually_prevents_reread(clear_data_cache, monkeypatch):
    load_data()

    def explode(*args, **kwargs):
        raise AssertionError("read_csv called again — cache is not working")

    monkeypatch.setattr(pd, "read_csv", explode)
    load_data()  # must not raise


STAT_KEYS = [
    "total_customers", "total_transactions", "total_amount",
    "suspicious_count", "suspicious_pct", "suspicious_amount",
    "ctr_eligible", "ctr_threshold",
    "kyc_verified", "kyc_expired", "kyc_pending", "kyc_verified_pct",
    "pep_count", "risk_distribution",
    "sar_total", "sar_by_status", "sar_by_type", "sar_total_amount",
]


@pytest.mark.parametrize("key", STAT_KEYS)
def test_get_stats_has_key(clear_data_cache, key):
    assert key in get_stats()


def test_get_stats_values_are_sane(clear_data_cache):
    s = get_stats()
    assert s["total_customers"] > 0
    assert s["total_transactions"] > 0
    assert 0 <= s["suspicious_pct"] <= 100
    assert 0 <= s["kyc_verified_pct"] <= 100
    assert s["suspicious_count"] <= s["total_transactions"]
    assert s["ctr_eligible"] <= s["total_transactions"]
    assert s["ctr_threshold"] > 0
    assert s["pep_count"] >= 0


def test_get_stats_dicts_are_json_safe(clear_data_cache):
    """Values must be plain ints, not numpy scalars — they get json.dumps'd by tools."""
    import json

    s = get_stats()
    for field in ("risk_distribution", "sar_by_status", "sar_by_type"):
        json.dumps(s[field])  # must not raise
        for k, v in s[field].items():
            assert isinstance(k, str)
            assert isinstance(v, int)


def test_data_dir_points_at_project_data():
    assert DATA_DIR.name == "data"
    assert DATA_DIR.parent.name == data_loader.Path(__file__).parent.parent.parent.name
