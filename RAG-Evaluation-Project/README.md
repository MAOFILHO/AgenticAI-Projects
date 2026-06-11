# RAG Pattern Comparison & Evaluation Pipeline

Compares **6 RAG patterns** against the **same 40-question evaluation dataset and
document corpus**, using a common evaluation framework (custom retrieval metrics +
LLM-as-judge generation metrics, plus RAGAS metrics) as the common evaluation harness
for every pattern.

## RAG Patterns Evaluated

| # | Pattern | Strategy |
|---|---------|----------|
| 1 | FAISS Similarity Search | FAISS vector store, top-K cosine similarity, LCEL RAG chain |
| 2 | FAISS MMR (Diversity) | FAISS + Maximal Marginal Relevance retrieval |
| 3 | ChromaDB Similarity Search | ChromaDB persistent vector store, top-K similarity |
| 4 | ChromaDB MMR (Diversity) | ChromaDB + MMR retrieval |
| 5 | Agentic RAG (ReAct + Iterative) | LangChain ReAct agent that calls a retrieval tool iteratively on SQLite DB, PDF documents and Tavily Web Search, reformulating queries |
| 6 | OpenAI File Search (Hosted Vector Store) | OpenAI Responses API + hosted Vector Store `file_search` tool |
| 7 | Multimodal Vision + Text RAG (SecureLife) | GPT-4o vision damage assessment + FAISS RAG over policy clauses, fused by a 3-node LangGraph into a coverage decision |

## Evaluation Framework

For **every** pattern above, the pipeline runs:

- **Retrieval metrics** (full 40-question dataset, no LLM calls): Hit Rate@K, MRR@K,
  Precision@K, Recall@K, nDCG@K — pure-Python implementations.
- **Generation metrics** (LLM-as-judge, sample of `E2E_SAMPLE_SIZE` questions, default 10):
  Answer Relevance, Groundedness, Hallucination Rate, and Coherence.
- **RAGAS metrics** (enabled by default, `ENABLE_RAGAS=true`): Faithfulness, Answer Relevancy,
  Context Precision, Context Recall.

At the end, the terminal prints a side-by-side comparison table and key differences
summary, and a multi-sheet Excel report is exported to `outputs/`.

Like patterns 1-5, it is traced to LangSmith when `LANGSMITH_API_KEY` is set.


### Pattern 7: Multimodal Vision + Text RAG (SecureLife)

Pattern 7 is a different shape of problem — a motor-insurance claims agent that
**looks at a damage photo and reads policy text** to make a coverage decision.
It is run as a separate demo (`src/patterns/multimodal_securelife.py`), not as
part of the 40-question retrieval/generation comparison, since its inputs
(images, a claim record) and outputs (a structured coverage decision) don't fit
the text-QA metric framework used by patterns 1-6.

**The Architecture**

<img width="909" height="449" alt="Screenshot 2026-06-10 at 9 49 29 PM" src="https://github.com/user-attachments/assets/21b53475-4432-40d6-a3aa-d30bcbb1d53c" />

For each of the 3 sample damage photos (front collision, side scratch, total
loss) against the same claim record (`CLM-2025-0001`), the pipeline runs:

1. **`vision_node`** — `gpt-4o` analyses the photo and returns a structured
   `DamageAssessment` (damage type, severity, estimated repair cost in INR,
   affected parts).
2. **`policy_node`** — semantic search (FAISS RAG) over the 10-clause
   SecureLife Motor Comprehensive policy document, returning the relevant
   coverage citations.
3. **`synthesize_node`** — cross-checks vision + policy + claim record and
   returns a structured `CoverageDecision` (APPROVE/REVIEW/REJECT, confidence,
   fraud signal vs. clause `FR-001`, cited clauses, reasoning, next steps).

<img width="1003" height="548" alt="Screenshot 2026-06-10 at 9 50 28 PM" src="https://github.com/user-attachments/assets/9526b5ad-f43c-4ee0-98be-88c9bbe0aca6" />

The claim record is loaded from `data/multimodal/SecureLife_claims.db` (SQLite database). 
Sample images live in `data/multimodal/`.

<img width="1027" height="397" alt="Screenshot 2026-06-10 at 9 51 03 PM" src="https://github.com/user-attachments/assets/0cc1307d-7373-4576-930c-858ea364a1fc" />


This pattern runs automatically as part of `python main.py` (and `--quick`),
after the patterns 1-6 comparison. Skip it with `--no-multimodal`, or run it
standalone:

```bash
python -c "from src.patterns.multimodal_securelife import run_demo; run_demo()"
```


## Requirements

- **Python: 3.13.13** (developed and smoke-tested on this version; any Python **3.11–3.13**
  should work, but 3.13.13 is the version this project's `requirements.txt` was pinned and
  verified against — `pip install -r requirements.txt` resolves cleanly with **no
  dependency conflicts** on 3.13.13).
- An **OpenAI API key** (`OPENAI_API_KEY`) — used for embeddings (`text-embedding-3-small`),
  the generator/judge LLM (`gpt-4.1-mini` by default), the agentic pattern, and the
  OpenAI File Search pattern.
- macOS / Linux / Windows supported. No GPU required (FAISS uses `faiss-cpu`).
- ~50 MB disk for the corpus (4 PDF papers + a Wikipedia JSONL sample, included in `data/`).

### Pinned core dependencies (`requirements.txt`)

```
langchain==1.3.6
langchain-core==1.4.3
langchain-openai==1.1.9
langchain-community==0.4.2
langchain-chroma==1.1.0
langchain-text-splitters==1.1.2
langchain-classic==1.0.7
faiss-cpu==1.13.0
chromadb==1.3.5
pymupdf==1.26.6
jq==1.10.0
openpyxl==3.1.5
numpy==2.3.4
python-dotenv==1.1.1
openai==2.8.1
langsmith==0.8.12
langgraph==1.2.4
langfuse==4.7.1
ragas==0.3.7
datasets==5.0.0
```

These versions were resolved and installed without conflicts in a clean
`python3 -m venv .venv` on Python 3.13.13. If you use a different Python version and hit
a resolver conflict, run `pip install -r requirements.txt` without strict pins (remove
`==x.y.z`) and let pip resolve a compatible set, then re-pin with `pip freeze`.

### RAGAS metrics

RAGAS (Faithfulness, Answer Relevancy, Context Precision, Context Recall) is **enabled by
default** (`ENABLE_RAGAS=true` in `.env.example`) and `ragas`/`datasets` are part of
`requirements.txt`.

`ragas` 0.3.x still does an unconditional import of
`langchain_community.chat_models.vertexai`, a module removed in `langchain-community`
0.4.x. `./install.sh` runs `scripts/patch_ragas_vertexai_shim.py`, which installs a small
stub module into the venv's `langchain_community` package so that import succeeds (the
stub is never actually used — all LLM calls in this project go through OpenAI).

<img width="1111" height="404" alt="Screenshot 2026-06-10 at 9 56 14 PM" src="https://github.com/user-attachments/assets/79745b63-e956-46b0-821f-4e1219ac13f4" />


Set `ENABLE_RAGAS=false` in `.env` to skip RAGAS metrics (fewer LLM calls, faster runs).
If `ENABLE_RAGAS=true` but `ragas` isn't importable, the pipeline logs a notice and skips
RAGAS metrics — it does not error.

## Setup

```bash
./install.sh                     # creates .venv, installs deps, runs smoke tests
cp .env.example .env             # then edit .env and add your OPENAI_API_KEY
source .venv/bin/activate
```

## Usage

```bash
# Smoke run: 1-2 sample questions for generation metrics, all 6 patterns
python main.py --quick

# Full run: 40-question retrieval eval + 10-question generation eval, all 6 patterns
python main.py

# Run only specific patterns (1-indexed, see table above)
python main.py --patterns 1 3 5
```

Each pattern prints a header like:

```
Now running the RAG Evaluation pipeline using: FAISS Similarity Search
  FAISS vector store, top-K similarity search, LCEL RAG chain
```

followed by its retrieval metrics, sampled generation results, and (if enabled) RAGAS
scores. After all selected patterns finish, a comparison table and an Excel report
(`outputs/<experiment_name>_<timestamp>.xlsx`) are produced.

## Configuration

All tunable parameters live in `src/config.py` and can be overridden via `.env`:

| Setting | Default | Description |
|---------|---------|-------------|
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model for all vector-store patterns |
| `GENERATOR_LLM` | `gpt-4.1-mini` | LLM used to generate answers |
| `JUDGE_LLM` | `gpt-4.1-mini` | LLM used as judge for generation metrics |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `200` | Document chunking |
| `TOP_K` | `5` | Retriever top-K |
| `MMR_FETCH_K` / `MMR_LAMBDA` | `20` / `0.5` | MMR retrieval params |
| `E2E_SAMPLE_SIZE` | `10` | # questions used for LLM-as-judge / RAGAS metrics |
| `ENABLE_RAGAS` | `true` | Enable RAGAS metrics (Faithfulness, Answer Relevancy, Context Precision, Context Recall) |

## Project Structure

```
RAG-Evaluation-Project/
├── main.py                  # CLI entrypoint
├── src/
│   ├── config.py            # all tunable settings
│   ├── data_loader.py        # loads 40-Q dataset + builds shared corpus
│   ├── evaluator.py          # evaluation framework, applied per pattern
│   ├── report.py             # comparison dashboard + Excel/JSON export
│   ├── patterns/              # the 7 RAG pattern implementations
│   └── metrics/               # retrieval metrics, LLM-as-judge, RAGAS
├── scripts/
│   ├── regression_check.py   # compares latest_results.json vs baseline.json
│   └── patch_ragas_vertexai_shim.py  # ragas/langchain-community compat shim
├── .github/workflows/
│   ├── smoke-tests.yml          # pytest on every push/PR
│   └── continuous-evaluation.yml # full eval + regression check (scheduled)
├── data/
│   ├── rag_eval_dataset_40_questions.json
│   ├── rag_docs/               # 4 PDF papers + Wikipedia JSONL sample
│   └── multimodal/              # SecureLife claims DB + 3 damage photos (pattern 7)
├── tests/test_smoke.py        # no-API-key smoke tests (pytest)
├── outputs/                    # generated Excel reports
├── requirements.txt
├── .env.example
└── install.sh
```

## Observability (LangSmith + Langfuse)

Observability is **on by default** -- the pipeline always wires up tracing for whichever
of the env vars below are set, and prints status (enabled/disabled + trace links) at
startup and in the final comparison report. No flag is required to enable it.

- **LangSmith** (`LANGSMITH_API_KEY`): traces every LangChain-based pattern run
  (patterns 1-5 and 7: FAISS/Chroma similarity & MMR, agentic RAG, multimodal SecureLife).
  Pattern 6 (OpenAI File Search) uses the raw OpenAI SDK and is **not** traced by
  LangSmith. Customize the project with `LANGSMITH_PROJECT`.
- **Langfuse** (`LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY`): traces **all 7 patterns**,
  including pattern 6 -- via the `langfuse.openai` drop-in client for the raw OpenAI SDK,
  and the Langfuse LangChain callback handler for patterns 1-5 and 7. Set `LANGFUSE_HOST`
  for a self-hosted instance (defaults to `https://cloud.langfuse.com`).

```
LangSmith tracing ENABLED (project: 'rag-pattern-comparison')
  View traces at: https://smith.langchain.com/o/-/projects/p/rag-pattern-comparison

Langfuse tracing ENABLED (covers all 7 patterns, including the raw
  OpenAI SDK File Search pattern that LangSmith cannot trace).
  View traces at: https://cloud.langfuse.com/project
```

If neither key is set, the pipeline runs normally with tracing simply inactive --
no error, no flag needed.

## Smoke Tests

`tests/test_smoke.py` validates dataset/corpus loading, the retrieval-metric math, and
report formatting **without calling the OpenAI API** (a dummy API key is used only to
construct client objects). Run with:

```bash
python -m pytest tests/test_smoke.py -q
```

For a real end-to-end check (calls OpenAI), use `python main.py --quick`.

## Continuous Evaluation & Regression Testing

Every `python main.py` run exports `outputs/latest_results.json` (per-pattern retrieval,
generation, and RAGAS metrics) in addition to the Excel report. `scripts/regression_check.py`
compares this against a saved baseline and exits non-zero if any metric regressed:

- **"Higher is better" metrics** (Hit Rate, MRR, Precision, Recall, nDCG, Answer Relevance,
  Groundedness, Coherence, RAGAS scores): fails if they drop more than
  `REGRESSION_RELATIVE_DROP_THRESHOLD` (default 10%) relative to baseline.
- **Hallucination Rate**: fails if it increases by more than
  `REGRESSION_HALLUCINATION_INCREASE_THRESHOLD` (default 0.10, absolute).

```bash
python main.py                                    # writes outputs/latest_results.json
python scripts/regression_check.py --save-baseline   # promote current run to baseline
# ... after code/prompt changes ...
python main.py
python scripts/regression_check.py                # compares latest vs baseline
```

Both thresholds are configurable via `.env` (`REGRESSION_RELATIVE_DROP_THRESHOLD`,
`REGRESSION_HALLUCINATION_INCREASE_THRESHOLD`).

### CI workflows (`.github/workflows/`)

- **`smoke-tests.yml`**: runs `pytest tests/test_smoke.py` on every push/PR (no API key needed).
- **`continuous-evaluation.yml`**: runs the full pipeline + regression check weekly (and
  on-demand via `workflow_dispatch`), uploading the Excel report and `latest_results.json`
  as artifacts. Requires an `OPENAI_API_KEY` repo secret (and optionally
  `LANGSMITH_API_KEY` / `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` for tracing); the job
  is skipped if `OPENAI_API_KEY` isn't set. Commit `outputs/baseline.json` to the repo once
  you're happy with a run, so future runs have something to compare against.


### Screenshots

<img width="1308" height="780" alt="Screenshot 2026-06-10 at 3 46 02 PM" src="https://github.com/user-attachments/assets/9d842707-97d1-454b-bf7a-f916163a13a2" />

<img width="1369" height="672" alt="Screenshot 2026-06-10 at 4 04 49 PM" src="https://github.com/user-attachments/assets/d264b406-6f1c-4d44-8098-a8d9e06a43d7" />

<img width="1360" height="891" alt="Screenshot 2026-06-10 at 4 05 46 PM" src="https://github.com/user-attachments/assets/72b7c2e5-3a54-45e5-a2f5-d574e13fc164" />

<img width="1366" height="911" alt="Screenshot 2026-06-10 at 4 14 46 PM" src="https://github.com/user-attachments/assets/94f8ad95-0758-48e5-929f-75ba97e0941b" />

<img width="1366" height="866" alt="Screenshot 2026-06-10 at 4 18 26 PM" src="https://github.com/user-attachments/assets/5e7d1bc4-7771-4b56-9ace-4774d50889d6" />

<img width="1374" height="457" alt="Screenshot 2026-06-10 at 4 19 07 PM" src="https://github.com/user-attachments/assets/7589e5c7-2ec4-4eec-be6f-263de257e8c6" />

<img width="1684" height="574" alt="Screenshot 2026-06-10 at 3 35 29 PM" src="https://github.com/user-attachments/assets/b16e8c02-2ccd-44be-9783-6acd1d6fe570" />

<img width="1680" height="887" alt="Screenshot 2026-06-10 at 3 36 29 PM" src="https://github.com/user-attachments/assets/91c82067-fd83-4f70-804e-1bc4839f3c6f" />

<img width="1677" height="887" alt="Screenshot 2026-06-10 at 3 36 49 PM" src="https://github.com/user-attachments/assets/be08463d-1387-4adb-a300-ea85998cb716" />

<img width="1119" height="891" alt="Screenshot 2026-06-10 at 3 37 02 PM" src="https://github.com/user-attachments/assets/39b93a36-8a75-4e3c-ac38-2dbbcb04f34f" />

<img width="1118" height="889" alt="Screenshot 2026-06-10 at 3 37 31 PM" src="https://github.com/user-attachments/assets/6f1cdf1f-c0f1-4360-844e-41df95e787d4" />

<img width="1117" height="891" alt="Screenshot 2026-06-10 at 3 37 47 PM" src="https://github.com/user-attachments/assets/5069282b-ed6a-4c0e-a413-cdbbcb4f412c" />

<img width="1682" height="854" alt="Screenshot 2026-06-10 at 3 38 28 PM" src="https://github.com/user-attachments/assets/e29f1d82-f45e-4e34-89a9-6b92eed34d0b" />

<img width="1006" height="845" alt="Screenshot 2026-06-10 at 3 38 48 PM" src="https://github.com/user-attachments/assets/695fdbca-1b37-4bd6-bcdf-bf4b3de1abd2" />

<img width="1005" height="853" alt="Screenshot 2026-06-10 at 3 39 07 PM" src="https://github.com/user-attachments/assets/e2821acf-5160-48b4-b00c-6d09df27265c" />

<img width="1005" height="897" alt="Screenshot 2026-06-10 at 3 39 34 PM" src="https://github.com/user-attachments/assets/200ceee6-8e58-426e-84a8-210f30195f39" />

<img width="1011" height="891" alt="Screenshot 2026-06-10 at 3 59 25 PM" src="https://github.com/user-attachments/assets/c1550e5f-933c-4f44-9983-52d422510970" />

<img width="1683" height="528" alt="Screenshot 2026-06-10 at 9 00 51 PM" src="https://github.com/user-attachments/assets/22b9d345-df88-4bc3-96a9-cbca5457b784" />

<img width="1683" height="825" alt="Screenshot 2026-06-10 at 9 03 07 PM" src="https://github.com/user-attachments/assets/99831778-9ab1-4030-9b42-190727b87924" />
