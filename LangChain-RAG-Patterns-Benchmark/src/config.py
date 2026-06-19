"""Central configuration for the RAG pattern comparison pipeline.

Change values here, then re-run main.py to re-evaluate with new settings.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Embedding Model ---
EMBEDDING_MODEL = "text-embedding-3-small"

# --- Generator LLM ---
GENERATOR_LLM = "gpt-4.1-mini"
GENERATOR_TEMPERATURE = 0

# --- Judge LLM (for LLM-as-judge generation metrics) ---
JUDGE_LLM = "gpt-4.1-mini"
JUDGE_TEMPERATURE = 0

# --- Document Chunking ---
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# --- Retrieval ---
TOP_K = 5
MMR_FETCH_K = 20
MMR_LAMBDA = 0.5

# --- Retrieval relevance threshold (word-overlap with gold context) ---
RELEVANCE_THRESHOLD = 0.3

# --- Evaluation sample size for end-to-end (LLM-as-judge / RAGAS) metrics ---
# Retrieval metrics always run on the full 40-question dataset.
# Generation metrics call the LLM multiple times per question, so we default
# to a smaller sample to keep smoke-test runs fast and cheap.
E2E_SAMPLE_SIZE = int(os.environ.get("E2E_SAMPLE_SIZE", "10"))

# --- Paths ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DOCS_DIR = os.path.join(DATA_DIR, "rag_docs")
EVAL_DATASET_PATH = os.path.join(DATA_DIR, "rag_eval_dataset_40_questions.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs")
INDEX_CACHE_DIR = os.path.join(PROJECT_ROOT, ".index_cache")

# --- Experiment metadata ---
EXPERIMENT_NAME = os.environ.get("EXPERIMENT_NAME", "rag_pattern_comparison")

# --- Feature flags ---
ENABLE_RAGAS = os.environ.get("ENABLE_RAGAS", "true").lower() == "true"

# --- Regression testing ---
# Max allowed relative drop in "higher is better" metrics (Hit Rate, MRR,
# Precision, Recall, nDCG, Answer Relevance, Groundedness, Coherence) and max
# allowed absolute increase in "lower is better" metrics (Hallucination Rate)
# before scripts/regression_check.py reports a regression and exits non-zero.
REGRESSION_RELATIVE_DROP_THRESHOLD = float(os.environ.get("REGRESSION_RELATIVE_DROP_THRESHOLD", "0.10"))
REGRESSION_HALLUCINATION_INCREASE_THRESHOLD = float(
    os.environ.get("REGRESSION_HALLUCINATION_INCREASE_THRESHOLD", "0.10")
)
BASELINE_RESULTS_PATH = os.path.join(OUTPUT_DIR, "baseline.json")
LATEST_RESULTS_PATH = os.path.join(OUTPUT_DIR, "latest_results.json")

# --- LangSmith tracing ---
# Set LANGSMITH_API_KEY (and optionally LANGSMITH_PROJECT) in .env to enable.
# When set, this also configures the standard LangChain tracing env vars so
# every chain/agent/LLM call in the pipeline is traced automatically.
LANGSMITH_API_KEY = os.environ.get("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.environ.get("LANGSMITH_PROJECT", "rag-pattern-comparison")
LANGSMITH_ENDPOINT = os.environ.get("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
TRACING_ENABLED = bool(LANGSMITH_API_KEY)

if TRACING_ENABLED:
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGSMITH_API_KEY", LANGSMITH_API_KEY)
    os.environ.setdefault("LANGCHAIN_API_KEY", LANGSMITH_API_KEY)
    os.environ.setdefault("LANGSMITH_PROJECT", LANGSMITH_PROJECT)
    os.environ.setdefault("LANGCHAIN_PROJECT", LANGSMITH_PROJECT)
    os.environ.setdefault("LANGSMITH_ENDPOINT", LANGSMITH_ENDPOINT)


def langsmith_project_url():
    """Return the LangSmith URL for this run's project, or None if tracing is disabled."""
    if not TRACING_ENABLED:
        return None
    return f"https://smith.langchain.com/o/-/projects/p/{LANGSMITH_PROJECT}"


# --- Langfuse tracing ---
# Observability is ON by default for every pattern, including the raw OpenAI
# SDK pattern (File Search) which LangSmith cannot trace. Set
# LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY in .env to activate; if unset, the
# pipeline runs normally with tracing simply inactive (no error).
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
LANGFUSE_TRACING_ENABLED = bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)

if LANGFUSE_TRACING_ENABLED:
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", LANGFUSE_PUBLIC_KEY)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", LANGFUSE_SECRET_KEY)
    os.environ.setdefault("LANGFUSE_HOST", LANGFUSE_HOST)


def langfuse_callback_handler():
    """Return a Langfuse CallbackHandler for LangChain chains/agents, or None if disabled."""
    if not LANGFUSE_TRACING_ENABLED:
        return None
    from langfuse.langchain import CallbackHandler

    return CallbackHandler()


def get_openai_client():
    """Return an OpenAI client class, Langfuse-wrapped (traced) if enabled."""
    if LANGFUSE_TRACING_ENABLED:
        from langfuse.openai import OpenAI
    else:
        from openai import OpenAI
    return OpenAI


def runnable_config():
    """RunnableConfig dict to pass to .invoke() so LangChain runs are traced by Langfuse."""
    handler = langfuse_callback_handler()
    return {"callbacks": [handler]} if handler else {}


def langfuse_project_url():
    if not LANGFUSE_TRACING_ENABLED:
        return None
    return f"{LANGFUSE_HOST}/project"
