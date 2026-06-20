#!/bin/bash
set -e

echo "============================================"
echo "  ShopSmart Support — Automated Setup"
echo "============================================"
echo

# Require Python 3.12 explicitly
PYTHON_CMD=""
if command -v python3.12 &>/dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3 &>/dev/null; then
    PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
    if [ "$PY_MINOR" -eq 12 ]; then
        PYTHON_CMD="python3"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "ERROR: Python 3.12 is required but not found."
    echo ""
    echo "Install it with one of:"
    echo "  brew install python@3.12"
    echo "  pyenv install 3.12.10"
    echo ""
    echo "Then re-run: make setup"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "Using $PYTHON_CMD ($PYTHON_VERSION) ✓"
echo

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Create virtual environment with Python 3.12
if [ ! -d ".venv" ]; then
    echo "[1/5] Creating virtual environment with $PYTHON_CMD..."
    $PYTHON_CMD -m venv .venv
else
    echo "[1/5] Virtual environment already exists."
fi

# Activate
echo "[2/5] Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "[3/5] Installing dependencies..."
pip install --upgrade pip setuptools wheel -q
pip install -e ".[dev]" -q

# Copy .env if needed
if [ ! -f ".env" ]; then
    echo "[4/5] Creating .env from template..."
    cp .env.example .env
    echo "  ⚠️  Please edit .env with your API keys before running."
else
    echo "[4/5] .env already exists."
fi

# Verify installation
echo "[5/5] Verifying installation..."
python -c "import shopsmart; print(f'  ShopSmart v{shopsmart.__version__} installed successfully')"
python -c "import sys; print(f'  Python {sys.version}')"

echo
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Run smoke tests:  make smoke"
echo "  3. Run full tests:   make test"
echo "  4. Start the app:    make app"
echo
