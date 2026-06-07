# 🛡️ SecureLife Claims Processing Hub

Designed and implemented a distributed, asynchronous AI agent pipeline for end-to-end insurance claims processing using a modern two-tier architecture: **LangGraph** and the **Model Context Protocol (MCP)** modern architecture. Built a **5-stage multi-agent workflow** (Triage, Document Verification, Fraud Analysis, Decisioning, Compliance Auditing) with guardrails for input sanitization and PII redaction. Enabled real-time conversational interaction via **Chainlit Client** and ensured full auditability through immutable database logging and transactional MCP operations.


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

# 2. Create and activate a virtual environment
python3.11 -m venv .venv
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

---

## Screenshots

<img width="1306" height="368" alt="Screenshot 2026-06-07 at 7 35 49 PM" src="https://github.com/user-attachments/assets/1c730ee9-7e4a-4634-82ca-88e1b4e7339b" />

<img width="1073" height="709" alt="Screenshot 2026-06-07 at 6 58 34 PM" src="https://github.com/user-attachments/assets/2f5061fe-d15d-4b9b-a5ca-96c3abb5f5e8" />

<img width="1028" height="621" alt="Screenshot 2026-06-07 at 6 59 15 PM" src="https://github.com/user-attachments/assets/36d0ec36-c2b0-46bf-9ebd-eefc136d1aa8" />

<img width="1003" height="729" alt="Screenshot 2026-06-07 at 7 00 27 PM" src="https://github.com/user-attachments/assets/dbf01a6d-3ef5-4dcb-96ce-075a655a46d1" />

<img width="1084" height="720" alt="Screenshot 2026-06-07 at 7 00 44 PM" src="https://github.com/user-attachments/assets/97f08b80-46c6-4343-80c3-20464ebe071f" />

<img width="1429" height="596" alt="Screenshot 2026-06-07 at 7 02 30 PM" src="https://github.com/user-attachments/assets/9d296e4c-deaf-494c-b52a-9c092de3d417" />

<img width="1425" height="629" alt="Screenshot 2026-06-07 at 7 03 24 PM" src="https://github.com/user-attachments/assets/ff6443ef-40d8-4224-a5e3-7bfe8660bd49" />

<img width="1428" height="662" alt="Screenshot 2026-06-07 at 7 05 18 PM" src="https://github.com/user-attachments/assets/b01e3e1d-25e2-4b4e-958f-763d53bcb08f" />

<img width="860" height="663" alt="Screenshot 2026-06-07 at 7 06 03 PM" src="https://github.com/user-attachments/assets/7d7e2e7b-94e5-44b9-9749-88ca7cc30964" />

<img width="853" height="665" alt="Screenshot 2026-06-07 at 7 06 35 PM" src="https://github.com/user-attachments/assets/d03ae3be-6c8e-44be-b221-56ed4d77736c" />


