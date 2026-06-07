# SecureLife Full Claims Pipeline
### PROJECT 5 · Agentic AI Track

A production-grade, multi-agent claims processing pipeline built with **LangGraph**, **FastMCP**, and **OpenAI GPT-4o-mini**. Processes 5 representative insurance claims end-to-end with guardrails, observability hooks, and a full audit trail written back to SQLite.

---

## Architecture

```
user_note ──▶ GuardrailPipeline.check_input
                        │
                        ▼
          ┌─────────────────────────────┐
          │  LangGraph (5 nodes)        │
          │                             │
          │  Triage ──▶ DocVerifier ──▶ │
          │  FraudAnalyst ──▶           │
          │  DecisionMaker ──▶          │
          │  ComplianceAuditor          │
          └──────────────┬──────────────┘
                         │
                         ▼
          GuardrailPipeline.check_output
                         │
                         ▼
                  SecureLife_claims.db
               (status + claim_history)
```

| Node | Role | MCP Tool |
|------|------|----------|
| Triage | Fetch claim + block injections | `fetch_claim` |
| DocVerifier | Check required vs submitted docs | `verify_documents` |
| FraudAnalyst | Sum fraud indicator weights | `calculate_fraud_score` |
| DecisionMaker | LLM → APPROVE / REVIEW / REJECT | — |
| ComplianceAuditor | Persist decision + audit row | `update_claim_status` |

---

## Quick Start

```bash
# 1. Python 3.11 recommended
python --version   # must be 3.11+

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY at minimum

# 5. Run the pipeline
python main.py
```

---

## Output Files (generated in `./output/`)

| File | Description |
|------|-------------|
| `langgraph_pipeline.png` | Mermaid-rendered LangGraph flow diagram |
| `langgraph_architecture.png` | Custom matplotlib architecture diagram |
| `batch_results.png` | Stacked-bar recommendations + latency chart |
| `langgraph_ascii.txt` | ASCII fallback if Mermaid PNG unavailable |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ | OpenAI API key |
| `LANGSMITH_API_KEY` | Optional | Enable LangSmith tracing |
| `LANGSMITH_PROJECT` | Optional | Project name (default: `securelife-m6-v2`) |
| `LANGFUSE_PUBLIC_KEY` | Optional | Enable Langfuse tracing |
| `LANGFUSE_SECRET_KEY` | Optional | Langfuse secret |
| `LANGFUSE_HOST` | Optional | Langfuse host (default: cloud.langfuse.com) |

---

## Project Structure

```
securelife_pipeline/
├── main.py                  # Full pipeline — run this
├── requirements.txt
├── .env.example             # Copy to .env and fill in keys
├── .gitignore
├── README.md
├── data/
│   └── SecureLife_claims.db # SQLite database (45 claims)
└── output/                  # Generated at runtime
    ├── langgraph_pipeline.png
    ├── langgraph_architecture.png
    └── batch_results.png
```

---

## What the Pipeline Does

1. **Picks 5 claims** — 1 CLEAN, 2 SUSPICIOUS, 2 INCOMPLETE
2. **Runs each through all 5 LangGraph nodes**
3. **Writes audit rows** to `claim_history` (one per claim)
4. **Updates** `claims.status` → APPROVED / UNDER_REVIEW / REJECTED
5. **Runs an adversarial test** with a prompt-injection payload — verifies DB remains intact
6. **Saves PNG charts** to `./output/`

---

## Python Version

Requires **Python 3.11+**. Tested on 3.11 and 3.12.  
`nest-asyncio` is applied at startup to allow sync `invoke` calls inside async runtimes.

---

## Notes

- The `.env` file is git-ignored — never commit your API keys.
- `data/SecureLife_claims.db` is git-ignored by default. Add it manually if your repo is private.
- If the Mermaid PNG render fails (requires `playwright` or `pyppeteer` in some environments), the pipeline falls back to an ASCII diagram and still saves the matplotlib architecture PNG.
