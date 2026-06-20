#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "============================================"
echo "  ShopSmart Support — Smoke Tests"
echo "============================================"
echo

# Activate venv if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "[1/3] Running offline smoke tests (no API key required)..."
python -m pytest tests/test_smoke.py::test_data_loads tests/test_smoke.py::test_state_schema_fields tests/test_smoke.py::test_classification_model tests/test_smoke.py::test_classification_model_validation -v

echo
echo "[2/3] Running PII tests..."
python -m pytest tests/test_pii.py -v

echo
echo "[3/3] Running tool tests..."
python -m pytest tests/test_tools.py -v

echo
echo "============================================"
echo "  Smoke tests complete!"
echo "============================================"
