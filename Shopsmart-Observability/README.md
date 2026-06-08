# ShopSmart Observability — Lab 22

Production observability for the ShopSmart AI support agent using **LangSmith** and **Langfuse** side-by-side. Same agent, same 5 tickets, two dashboards.

## What it does

- Runs 5 support tickets through a LangGraph routing agent (classify → specialist handler)
- Auto-traces every LangChain/LangGraph call via **LangSmith** (env-var, zero code change)
- Traces the same run via **Langfuse** (`CallbackHandler` pattern)
- Prints a side-by-side latency table and saves a comparison chart (`observability_report.png`)

## Python version

Python **3.11+** required.

## Setup

```bash
# 1. Clone / unzip the project
cd shopsmart-observability

# 2. Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure keys
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY, LANGSMITH_API_KEY,
# LANGFUSE_PUBLIC_KEY, and LANGFUSE_SECRET_KEY

# 5. Run
python main.py
```

## Project structure

```
shopsmart-observability/
├── main.py            # Entry point — orchestrates both platform runs
├── agent.py           # LangGraph StateGraph (classify → route → handle)
├── data.py            # Orders DB, policies, test tickets
├── observability.py   # LangSmith + Langfuse setup helpers
├── charts.py          # Latency bar chart + category pie chart
├── requirements.txt
├── .env.example
└── .gitignore
```

## Observability platforms

| | LangSmith | Langfuse |
|---|---|---|
| **License** | Proprietary SaaS (free tier) | MIT Open Source |
| **Self-host** | Enterprise only | Yes (Docker / K8s) |
| **Setup** | `LANGSMITH_TRACING=true` env var | `CallbackHandler` in `config` |
| **Best for** | LangChain shops, fast setup | Data sovereignty, OSS-first |

Both are optional — the agent runs and prints results even if neither platform is configured.

## Output

- Console: per-ticket category, latency, response length; comparison table
- File: `observability_report.png` — latency bar chart + category distribution pie

## Key env vars

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | OpenAI API key |
| `LANGSMITH_API_KEY` | Optional | Enables LangSmith tracing |
| `LANGSMITH_PROJECT` | Optional | Project name (default: `shopsmart-spine-a`) |
| `LANGFUSE_PUBLIC_KEY` | Optional | Langfuse public key |
| `LANGFUSE_SECRET_KEY` | Optional | Langfuse secret key |
| `LANGFUSE_HOST` | Optional | Langfuse host (default: `https://us.cloud.langfuse.com`) |
