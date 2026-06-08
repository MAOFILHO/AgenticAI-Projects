# RegSentinel — Multi-Source Compliance Intelligence

> **Author:** Marcos Oliveira · K21 Agentic AI Mastery (Batch 4) · June 2026

An eval-driven compliance intelligence pipeline that automates regulatory synthesis, PII redaction, and multimodal identity verification — reducing manual audit cycles from ~80 hrs/quarter to minutes.

---

## Architecture

```
START ─┬─► regulation ─┐
       ├─► transaction ─┼─► classify ─► score ─► format ─► critic ─► (PASS/cap) ─► END
       └─► audit ───────┘                                     └─► (fail) ─► refiner ─┘
```

| Agentic Pattern | Where used |
|---|---|
| Parallel Fan-out | 3 worker nodes hit SQL, JSON, and RAG concurrently |
| Evaluator-Optimizer (Reflection) | Critic/Refiner loop (≤ 3 iterations) |
| Conditional Routing | Guardrail gate + critic exit condition |
| Structured Output | Pydantic schema on vision + LLM-judge nodes |

---

## Tech Stack

| Layer | Choice |
|---|---|
| Orchestration | LangGraph ≥ 0.2 |
| LLM | `gpt-4o-mini` (configurable via `.env`) |
| Embeddings / RAG | `text-embedding-3-small` + Chroma |
| Evaluation | LLM-as-judge + deterministic citation check |
| Observability | LangSmith (optional) |
| Data | `fft_data/` — SQLite + JSON + Markdown |

---

## Project Layout

```
regsentinel/
├── .env.example          # copy to .env and fill keys
├── .gitignore
├── README.md
├── requirements.txt
├── run_regsentinel.py    # main CLI entrypoint
├── fft_data/             # dataset (extract from fft_data.zip)
│   ├── fft_bank.db
│   ├── audit_events.json
│   └── regulations/
└── src/
    ├── config.py         # env loading + path constants
    ├── data_loader.py    # SQL helper + audit log loader
    ├── rag.py            # Chroma vector store over regulation corpus
    ├── tools.py          # 5 compliance tools
    ├── guardrails.py     # Task 1 — prompt-injection detection
    ├── pii_redaction.py  # Task 2 — GLBA PII masking
    ├── state.py          # ComplianceState TypedDict
    ├── nodes.py          # all LangGraph nodes
    ├── graph.py          # graph assembly + compilation
    ├── observability.py  # Task 3 — LangSmith tracing
    ├── evaluation.py     # Task 4 — citation accuracy + LLM-as-judge
    └── cip_multimodal.py # Task 5 — vision KYC extraction (stretch)
```

---

## Setup & Run

### Requirements
- Python ≥ 3.11
- `fft_data/` extracted from `fft_data.zip` (already done if you cloned the repo)

### 1 — Install dependencies
```bash
pip install -r requirements.txt
```

### 2 — Configure credentials
```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY (and optionally LANGSMITH_API_KEY)
```

### 3 — Run the pipeline
```bash
# Full pipeline — generates Q3 2026 Compliance Report
python run_regsentinel.py

# Pipeline + evaluation metrics (Task 4)
python run_regsentinel.py --eval

# Pipeline + multimodal CIP verification (Task 5 stretch)
python run_regsentinel.py --cip

# Everything
python run_regsentinel.py --eval --cip
```

---

## Capstone Tasks Implemented

| Task | Module | Description |
|---|---|---|
| Task 1 — Guardrails | `src/guardrails.py` | Regex-based prompt-injection detection on transaction memos |
| Task 2 — PII Redaction | `src/pii_redaction.py` | SSN / EIN / account / name masking (GLBA Safeguards Rule) |
| Task 3 — Observability | `src/observability.py` | LangSmith tracing via env vars — no-op if key absent |
| Task 4 — Evaluation | `src/evaluation.py` | Deterministic citation check + LLM-as-judge (faithfulness, completeness) |
| Task 5 — Multimodal CIP | `src/cip_multimodal.py` | Vision-based KYC document field extraction (stretch) |

---

## Evaluation Targets

| Metric | Method | Target |
|---|---|---|
| Faithfulness | LLM-as-judge | ≥ 0.85 |
| Citation accuracy | Exact-match vs DB | ≥ 0.90 |
| Red-flag recall | Pattern match | ≥ 0.80 |

---

## Data Sources

| Source | Format | Loaded via |
|---|---|---|
| customers / accounts / transactions | SQLite `fft_bank.db` | SQL |
| IT audit events | `audit_events.json` | JSON |
| Regulatory corpus (15 docs) | `regulations/*.md` | RAG / Chroma |
