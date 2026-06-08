"""Configuration: load .env and expose path constants."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (one level up from src/)
_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env")

# ── API keys ───────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
LANGSMITH_API_KEY: str = os.environ.get("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT: str = os.environ.get("LANGSMITH_PROJECT", "RegSentinel-Capstone-v2")

# ── Model ─────────────────────────────────────────────────────────────────────
OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL: str = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

# ── Data paths ────────────────────────────────────────────────────────────────
FFT_DATA_DIR: Path = _ROOT / "fft_data"
FFT_DB_PATH: Path = FFT_DATA_DIR / "fft_bank.db"
FFT_AUDIT_PATH: Path = FFT_DATA_DIR / "audit_events.json"
FFT_REG_DIR: Path = FFT_DATA_DIR / "regulations"

# Validate critical env vars at import time
if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY not set.\n"
        "  Create a .env file in the project root and add:\n"
        "    OPENAI_API_KEY=sk-...\n"
        "  See .env.example for the full template."
    )

if not FFT_DB_PATH.exists():
    raise FileNotFoundError(
        f"{FFT_DB_PATH} not found.\n"
        "  Unzip fft_data.zip into the project root:\n"
        "    unzip fft_data.zip"
    )
