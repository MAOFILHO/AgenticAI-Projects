# ShopSmart Observability

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


## Screenshots

<img width="1323" height="379" alt="Screenshot 2026-06-07 at 7 54 10 PM" src="https://github.com/user-attachments/assets/3562a730-bec1-4ea7-912f-045883cbcb2f" />

<img width="990" height="707" alt="Screenshot 2026-06-07 at 7 59 09 PM" src="https://github.com/user-attachments/assets/6aef50f2-b229-4d03-9a46-1488b634ef09" />

<img width="1310" height="494" alt="Screenshot 2026-06-07 at 7 58 21 PM" src="https://github.com/user-attachments/assets/62087c9c-417f-42b8-b6cf-a5cf62023871" />

<img width="1145" height="691" alt="Screenshot 2026-06-07 at 8 00 05 PM" src="https://github.com/user-attachments/assets/40945053-7d68-442b-b17e-f9472a407196" />

<img width="1428" height="699" alt="Screenshot 2026-06-07 at 8 00 28 PM" src="https://github.com/user-attachments/assets/48a37ece-ec51-4c62-8a69-807403273d74" />

<img width="1048" height="621" alt="Screenshot 2026-06-07 at 8 00 49 PM" src="https://github.com/user-attachments/assets/4a36800e-12ad-41da-bc0d-b381c95d8001" />

<img width="1048" height="627" alt="Screenshot 2026-06-07 at 8 01 29 PM" src="https://github.com/user-attachments/assets/44bec46f-6bbd-4ea5-bf67-428daed54cda" />

<img width="1433" height="660" alt="Screenshot 2026-06-07 at 8 02 50 PM" src="https://github.com/user-attachments/assets/1651f686-9ded-4cd9-9adb-a2888c6acfdd" />

<img width="858" height="658" alt="Screenshot 2026-06-07 at 8 03 07 PM" src="https://github.com/user-attachments/assets/49d4fa52-0b33-4106-8bde-68f4bff6c08d" />

<img width="859" height="662" alt="Screenshot 2026-06-07 at 8 03 51 PM" src="https://github.com/user-attachments/assets/e895de53-7a4d-41f6-804a-454ad22c398d" />

