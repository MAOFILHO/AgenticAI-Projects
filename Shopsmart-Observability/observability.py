"""Observability bootstrap — LangSmith and Langfuse."""

import os


# ---------------------------------------------------------------------------
# LangSmith
# ---------------------------------------------------------------------------

def setup_langsmith() -> bool:
    """Enable LangSmith auto-tracing if API key is present. Returns True if active."""
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        print("[LangSmith] LANGSMITH_API_KEY not set — tracing disabled.")
        return False

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ.setdefault("LANGSMITH_PROJECT", "shopsmart-spine-a")

    print("[LangSmith] Auto-tracing enabled.")
    print(f"  Project : {os.environ['LANGSMITH_PROJECT']}")
    print(f"  API key : {'*' * 12}{api_key[-4:]}")
    print("  Dashboard: https://smith.langchain.com/")
    return True


def score_routing_langsmith(query: str, expected: str, actual: str) -> dict:
    """
    Log a custom routing-accuracy score to LangSmith via @traceable.
    Only called when LangSmith is active.
    """
    try:
        from langsmith import traceable

        @traceable(name="score_routing_accuracy", tags=["eval", "v1"])
        def _score(q: str, exp: str, act: str) -> dict:
            correct = exp == act
            return {
                "correct": correct,
                "score": 1.0 if correct else 0.0,
                "expected": exp,
                "actual": act,
            }

        return _score(query, expected, actual)
    except Exception as exc:
        print(f"[LangSmith] Score error: {exc}")
        return {}


# ---------------------------------------------------------------------------
# Langfuse
# ---------------------------------------------------------------------------

def setup_langfuse():
    """
    Build a Langfuse CallbackHandler if keys are present.
    Returns the handler (or None) and a bool indicating whether it's active.
    """
    pub_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    sec_key = os.getenv("LANGFUSE_SECRET_KEY")

    if not pub_key or not sec_key:
        print("[Langfuse] LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set — tracing disabled.")
        return None, False

    host = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
    os.environ.setdefault("LANGFUSE_HOST", host)

    try:
        from langfuse.langchain import CallbackHandler
        handler = CallbackHandler()
        print("[Langfuse] CallbackHandler ready.")
        print(f"  Host      : {host}")
        print(f"  Public key: {pub_key[:8]}...")
        print("  Dashboard : https://us.cloud.langfuse.com")
        return handler, True
    except Exception as exc:
        print(f"[Langfuse] Setup error: {exc}")
        return None, False


def flush_langfuse() -> None:
    """Flush buffered events to Langfuse before process exit."""
    try:
        from langfuse import get_client
        get_client().flush()
        print("[Langfuse] Events flushed.")
    except Exception:
        pass


def score_routing_langfuse(trace_id: str, actual: str, expected: str) -> None:
    """
    Push a routing-accuracy score to a Langfuse trace.
    Demonstrates the scoring API pattern.
    """
    try:
        from langfuse import get_client
        lf = get_client()
        lf.score(
            trace_id=trace_id,
            name="route_accuracy",
            value=1.0 if actual == expected else 0.0,
            comment=f"Routed to '{actual}' (expected '{expected}')",
        )
    except Exception as exc:
        print(f"[Langfuse] Score error: {exc}")
