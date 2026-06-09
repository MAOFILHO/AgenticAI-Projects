# MidwestBank AML Compliance Pipeline — 5-ADK Comparison

Runs the same **BSA/AML compliance reporting pipeline** using five different agentic AI frameworks side by side, then displays a comparison of architecture, timing, and key differences.

## Business Case

**MidwestBank** needs to generate a FinCEN BSA/AML compliance report. The pipeline:
1. Analyses transaction data for suspicious activity and CTR eligibility
2. Reviews SAR (Suspicious Activity Report) filing status
3. Assesses KYC/CDD compliance (expired, pending, PEP customers)
4. Detects AML patterns (structuring, layering, high-velocity)
5. Generates a structured regulatory compliance report

## Frameworks

| # | Framework | Orchestration Model | Lab Reference |
|---|-----------|--------------------|----|
| 1 | **LangGraph** | Graph (nodes + edges, Send fan-out) | Lab 10 |
| 2 | **OpenAI Agent SDK** | Handoff-based (triage → specialists) | Lab 13 |
| 3 | **CrewAI** | Role-based sequential pipeline | Lab 15 |
| 4 | **AutoGen** | Group chat (RoundRobin) | Lab 16 |
| 5 | **Google ADK** | Parallel + Sequential + Loop agents | Lab 27 |

## Setup

**Python 3.11+ required.** Tested on Python 3.13.13.

```bash
# 1. Enter the project directory
cd Compare-ADKs-Project

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

# 3. Install dependencies (two-phase — see note below)
bash install.sh

# 4. Configure API keys
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

> **Why two phases?** `crewai 1.14.6` pins `opentelemetry-api~=1.34.0` but
> `google-adk 2.2.0` requires `>=1.36`. These are mutually exclusive in a
> single `pip install` pass. `install.sh` installs google-adk first (setting
> opentelemetry to 1.41), then installs crewai with `--no-deps` to bypass the
> stale pin. CrewAI works fine at runtime with opentelemetry 1.41 — the pin
> just hasn't been updated upstream yet.

## Running

```bash
# Run all 5 frameworks sequentially
python main.py

# Run only one framework
python main.py --only langgraph
python main.py --only openai_agents
python main.py --only crewai
python main.py --only autogen
python main.py --only google_adk

# Skip a framework
python main.py --skip google_adk
```

## Expected Output

For each framework, the terminal shows:
```
============================================================
  Now running the pipeline using LangGraph
============================================================
[LangGraph] Report generated (420 words)
# MidwestBank — FinCEN BSA/AML Compliance Report Q4
...
```

At the end:
```
======================================================================
  ADK FRAMEWORKS COMPARISON — MIDWESTBANK COMPLIANCE PIPELINE
======================================================================
Framework              Status     Time(s)    LLM Calls    Report Words
----------------------------------------------------------------------
LangGraph              success    18.4       6            420
OpenAI Agent SDK       success    22.1       4            380
CrewAI                 success    25.6       3            445
AutoGen                success    19.8       5            390
Google ADK             success    21.3       7            410

ARCHITECTURAL COMPARISON
...
KEY DIFFERENCES SUMMARY
...
```

## Project Structure

```
compare-adks/
├── main.py                         # Entry point — run all 5 frameworks
├── shared/
│   ├── data_loader.py              # Load MidwestBank dataset
│   ├── tools.py                    # Shared tool functions
│   └── metrics.py                  # Timing + metrics tracking
├── runners/
│   ├── langgraph_runner.py         # LangGraph implementation
│   ├── openai_agents_runner.py     # OpenAI Agents SDK implementation
│   ├── crewai_runner.py            # CrewAI implementation
│   ├── autogen_runner.py           # AutoGen implementation
│   └── google_adk_runner.py        # Google ADK implementation
├── comparison/
│   └── report.py                   # Comparison report generator
├── data/                           # MidwestBank dataset (Lab 10)
│   ├── customers.csv
│   ├── transactions.csv
│   ├── sar_filings.csv
│   ├── prior_findings.csv
│   ├── regulatory_thresholds.json
│   ├── fincen_template.md
│   ├── occ_template.md
│   └── state_template.md
├── .env.example
├── requirements.txt
└── README.md
```

## Notes

- All frameworks use `gpt-4o-mini` by default (set `OPENAI_MODEL` in `.env` to override)
- Google ADK uses LiteLLM to route to OpenAI — no `GOOGLE_API_KEY` required
- LangGraph uses `MemorySaver` (in-memory) — no external storage needed
- AutoGen pre-fetches data into agent context to avoid tool-call overhead
- Each runner is independent — no shared state between framework runs

## Platform

Linux / macOS / Windows supported. Python 3.11+.
