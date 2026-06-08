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
| Task 2 — PII Redaction | `src/pii_redaction.py` | SSN / EIN / account/name masking (GLBA Safeguards Rule) |
| Task 3 — Observability | `src/observability.py` | LangSmith tracing via env vars — no-op if key absent |
| Task 4 — Evaluation | `src/evaluation.py` | Deterministic citation check + LLM-as-judge (faithfulness, completeness) |
| Task 5 — Multimodal CIP | `src/cip_multimodal.py` | Vision-based KYC document field extraction (stretch) |

---

## Agentic Patterns Used — and why

**Parallel Fan-out** — Chosen to query Regulations, Transactions, and SIEM logs simultaneously, minimizing latency in the data retrieval phase.

**Evaluator-Optimizer (Reflection)** — Used in the Synthesis loop to critique drafts for faithfulness, ensuring strict adherence to audit evidence before final submission.

**Conditional Routing** — Implemented to separate valid user requests from blocked prompt-injection attempts, safeguarding the integrity of downstream nodes.

**Structured Output** — Enforced via JSON schema constraints to guarantee that the Multimodal CIP node and LLM-Judge nodes return parsable data, eliminating regex fragility.

---

## Evaluation Targets

| Metric | Method | Target | Score |
|---|---|---|---|
| Faithfulness | LLM-as-judge | ≥ 0.85 | 0.92 |
| Citation accuracy | Exact-match vs DB | ≥ 0.90 | 0.95 |
| Red-flag recall | Pattern match | ≥ 0.80 | 0.88 |

---

## Data Sources

| Source | Format | Loaded via |
|---|---|---|
| customers / accounts / transactions | SQLite `fft_bank.db` | SQL |
| IT audit events | `audit_events.json` | JSON |
| Regulatory corpus (15 docs) | `regulations/*.md` | RAG / Chroma |

---

## Screenshots

<img width="1189" height="761" alt="Screenshot 2026-06-08 at 4 53 41 PM" src="https://github.com/user-attachments/assets/977fa980-7acb-43d8-8354-a65e622f8be0" />

<img width="1305" height="759" alt="Screenshot 2026-06-08 at 4 41 50 PM" src="https://github.com/user-attachments/assets/08913c43-8906-480f-8b5f-915d849ef5da" />

<img width="1009" height="709" alt="Screenshot 2026-06-08 at 4 42 08 PM" src="https://github.com/user-attachments/assets/0299c41c-3fba-4186-98cb-95731a204f89" />

<img width="1006" height="707" alt="Screenshot 2026-06-08 at 4 42 23 PM" src="https://github.com/user-attachments/assets/5f908378-eb2e-49f3-825f-a8846f6d8d11" />

<img width="1430" height="431" alt="Screenshot 2026-06-08 at 4 43 45 PM" src="https://github.com/user-attachments/assets/0e9e7f99-f1ab-4ffe-9490-b12952209300" />

<img width="954" height="705" alt="Screenshot 2026-06-08 at 4 44 09 PM" src="https://github.com/user-attachments/assets/39c75bd3-349c-416f-a863-70e3c91d4704" />

<img width="1013" height="710" alt="Screenshot 2026-06-08 at 4 46 44 PM" src="https://github.com/user-attachments/assets/dd1b2a32-54cc-4d14-a078-88516704d2ed" />

<img width="1004" height="710" alt="Screenshot 2026-06-08 at 4 47 05 PM" src="https://github.com/user-attachments/assets/47aba0b0-b702-459f-b3d5-187cc3ea987a" />

<img width="953" height="705" alt="Screenshot 2026-06-08 at 4 48 51 PM" src="https://github.com/user-attachments/assets/f0c1ffd5-c355-488d-b1f6-42b3ec5ebe0b" />

<img width="951" height="701" alt="Screenshot 2026-06-08 at 4 49 25 PM" src="https://github.com/user-attachments/assets/aba9c1cb-60c9-4046-be69-ec3a453ae4bf" />

<img width="1017" height="709" alt="Screenshot 2026-06-08 at 4 51 49 PM" src="https://github.com/user-attachments/assets/dd7d0984-31cf-47cc-a7ba-b2103e57998e" />

<img width="1007" height="712" alt="Screenshot 2026-06-08 at 4 52 09 PM" src="https://github.com/user-attachments/assets/8fb963f3-5842-4111-8853-f81ae6086302" />




