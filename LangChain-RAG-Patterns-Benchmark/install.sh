#!/usr/bin/env bash
# Set up a virtual environment and install dependencies for the RAG pattern
# comparison project. Run from this directory: ./install.sh
set -e

echo "=== Creating virtual environment (.venv) ==="
python3 -m venv .venv
source .venv/bin/activate

echo "=== Upgrading pip ==="
pip install --upgrade pip -q

echo "=== Installing core dependencies ==="
pip install -r requirements.txt

echo "=== Patching ragas/langchain-community compatibility shim ==="
python scripts/patch_ragas_vertexai_shim.py

echo "=== Verifying imports ==="
python -c "
import langchain, langchain_openai, langchain_community, langchain_chroma
import faiss, chromadb, fitz, openpyxl, numpy, openai
print('  langchain          OK')
print('  langchain_openai   OK')
print('  langchain_community OK')
print('  langchain_chroma   OK')
print('  faiss              OK')
print('  chromadb           OK')
print('  pymupdf (fitz)     OK')
print('  openai             OK')
"

echo ""
echo "=== Running smoke tests (no API key required) ==="
python tests/test_smoke.py

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. cp .env.example .env and add your OPENAI_API_KEY"
echo "  2. source .venv/bin/activate"
echo "  3. python main.py --quick   # fast end-to-end smoke run"
echo "  4. python main.py           # full comparison across all 6 patterns"
