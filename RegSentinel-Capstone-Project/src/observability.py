"""Task 3 — Observability: configure LangSmith tracing from environment variables."""
import os

from src.config import LANGSMITH_API_KEY, LANGSMITH_PROJECT


def setup_observability() -> bool:
    """Enable LangSmith tracing if LANGSMITH_API_KEY is present in .env.

    Returns True if tracing was activated, False if the key is absent (graceful no-op).
    """
    if not LANGSMITH_API_KEY:
        print("⚠️  LANGSMITH_API_KEY not set — pipeline runs without tracing.")
        print("   Add LANGSMITH_API_KEY=ls__... to your .env to enable LangSmith.")
        return False

    os.environ["LANGCHAIN_API_KEY"]     = LANGSMITH_API_KEY
    os.environ["LANGSMITH_API_KEY"]     = LANGSMITH_API_KEY   # backwards-compat
    os.environ["LANGCHAIN_TRACING_V2"]  = "true"
    os.environ["LANGCHAIN_PROJECT"]     = LANGSMITH_PROJECT

    print(f"🚀 LangSmith tracing enabled → project: {LANGSMITH_PROJECT}")
    return True
