# ShopSmart Customer Support — Multi-Agent System

### The Problem
ShopSmart is a mid-size e-commerce platform processing 50,000 customer support tickets per day. Their current system is a simple router (what we built in Lab 5) that classifies tickets and sends them to human agents. This approach has several limitations:

### Current Pain Point	            Impact
Human agents handle ALL tickets	High cost, slow response times
No automated order lookups	      Agents spend 40% of time just looking up order status
No policy consistency	            Different agents give different answers about return policies
Platinum customers wait in queue	VIP customers get the same treatment as everyone else
No conversation memory	            Customers repeat themselves when they call back

### The Solution: Multi-Agent System
We are building a Supervisor Multi-Agent System that:

Supervisor Router classifies incoming tickets using LLM-based structured output
Quick Answer Node handles simple order status lookups without an LLM (deterministic path)
4 Specialist Sub-Agents handle complex tickets with domain-specific tools
RAG Knowledge Base ensures consistent policy answers across all specialists
HITL Escalation routes platinum customers and critical tickets to human managers
PII Redaction protects customer data before it reaches any LLM
Memory maintains conversation context across multi-turn interactions

<img width="899" height="369" alt="Screenshot 2026-06-04 at 10 17 55 PM" src="https://github.com/user-attachments/assets/970aa548-3da6-420a-a340-74ddedb50317" />


### Why This Architecture?
Not every path needs AI: Simple order status queries use deterministic lookups (fast, cheap, reliable)
Specialists outperform generalists: Each sub-agent has focused tools and prompts
Humans stay in the loop: Critical decisions still go to human managers
RAG ensures consistency: All agents reference the same policy knowledge base


> **Project · Spine A Full Build**  
> LangChain v0.3 · LangGraph · FAISS RAG · HITL · MemorySaver

## Overview

A production-grade multi-agent customer support system for the fictitious e-commerce platform **ShopSmart**. Built as the capstone of the Spine A track, it combines every pattern into a single cohesive workflow.

### Architecture

```
Incoming Ticket
      │
  [PII Redaction]
      │
  [Supervisor Router] ← LLM classifies ticket + applies business rules
      │
      ├──► Quick Answer          (deterministic order lookup — zero LLM cost)
      ├──► Order Specialist      (LangGraph ReAct agent + 3 tools)
      ├──► Returns Specialist    (LangGraph ReAct agent + 4 tools)
      ├──► Billing Specialist    (LangGraph ReAct agent + 4 tools)
      ├──► Product Specialist    (LangGraph ReAct agent + 3 tools)
      └──► Escalation HITL       (interrupt() → human review → Command(resume=…))
                │
          [Response Formatter]
                │
          Final Customer Response
```

### Patterns Implemented

| Pattern | Description |
|---|---|
| **Supervisor Routing** | LLM structured output (Pydantic) classifies every ticket |
| **Specialist Sub-Agents** | 4 domain agents with focused tools via `langgraph.prebuilt.create_react_agent` |
| **Deterministic Quick-Answer** | Simple order status handled without any LLM call |
| **RAG Policy Lookup** | FAISS + `text-embedding-3-small` for consistent policy answers |
| **PII Redaction** | Regex + database-driven scrubbing before any LLM sees the text |
| **HITL Escalation** | `interrupt()` + `Command(resume=…)` for platinum/critical tickets |
| **Thread Memory** | `MemorySaver` for multi-turn conversation continuity |
| **Cross-Session Store** | `InMemoryStore` for customer history across sessions |

---

## Requirements

- Python **3.11+**
- An **OpenAI API key** (GPT-4o-mini access at minimum)

---

## Setup

### 1. Install Python 3.11 (Mac)

```bash
brew install python@3.11
```

### 2. Clone / unzip the project

```bash
cd Customer-Support-MultiAgent
```

### 3. Create a virtual environment

```bash
/opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate
```

> You should see `(.venv)` in your terminal prompt before proceeding.

### 4. Install dependencies

Run each install separately to avoid version conflicts:

```bash
pip install langchain
pip install langchain-openai
pip install langchain-community
pip install langchain-text-splitters
pip install langgraph
pip install faiss-cpu
pip install pydantic
pip install python-dotenv
```

### 5. Configure your API key

```bash
cp .env.example .env
```

Open `.env` and set your key:

```
OPENAI_API_KEY=sk-your-key-here
```

### 6. Run

```bash
python main.py
```

---

## Project Structure

```
Customer-Support-MultiAgent/
├── main.py          # Orchestrator — bootstrap + run all test cases
├── config.py        # LLM instances + env loading
├── data_loader.py   # Load JSON/MD files and build O(1) indexes
├── pii.py           # PII redaction and restoration
├── rag.py           # FAISS RAG knowledge base from policies.md
├── state.py         # CustomerSupportState TypedDict + TicketClassification Pydantic model
├── tools.py         # 10 domain tools (injected with live data)
├── nodes.py         # All node functions: supervisor, specialists, HITL, formatter
├── graph.py         # StateGraph assembly and compilation
├── data/
│   ├── customers.json
│   ├── orders.json
│   ├── products.json
│   ├── tickets.json
│   └── policies.md
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Data

| File | Records | Description |
|---|---|---|
| `customers.json` | 10 | bronze / silver / platinum tiers |
| `orders.json` | 100 | delivered / in_transit / processing / cancelled |
| `products.json` | 20 | Electronics, Clothing, Sports, Home, Books |
| `tickets.json` | 100 | 6 categories, 4 priority levels |
| `policies.md` | — | Return, shipping, billing, escalation policies |

---

## Tools

| # | Tool | Description |
|---|---|---|
| 1 | `lookup_customer` | Customer profile by ID |
| 2 | `lookup_order` | Order detail by order ID |
| 3 | `search_orders_by_customer` | All orders for a customer |
| 4 | `check_return_eligibility` | Return window check (30-day standard, 15-day electronics) |
| 5 | `lookup_product` | Product detail + FAQ |
| 6 | `search_products` | Case-insensitive name/category search |
| 7 | `policy_lookup` | Semantic RAG search over policies.md |
| 8 | `calculate_refund` | Full vs. partial refund calculation |
| 9 | `check_billing_status` | 5 most recent billing records |
| 10 | `escalate_to_manager` | Creates escalation ID |

---

## Escalation Logic

A ticket is escalated to HITL when any of the following apply:

- Customer tier is **platinum** AND priority is `high` or `critical`
- Category is `escalation` (customer explicitly requests a manager)
- Classification confidence is below **0.6**
- Ticket mentions legal action, social-media threats, or disputes over $500

---

## Model Configuration

| Variable | Default | Purpose |
|---|---|---|
| `PRIMARY_MODEL` | `gpt-5-mini` | Supervisor classification + specialist agents |
| `SECONDARY_MODEL` | `gpt-4o-mini` | Response formatting (temperature=0.3) |

Override in `.env`:

```
PRIMARY_MODEL=gpt-5-mini
SECONDARY_MODEL=gpt-4o-mini
```

---

## Key Takeaways

1. **Separate routing from handling.** The supervisor classifies; the specialists act. Each concern is independently testable.
2. **Not every path needs AI.** The quick-answer node saves tokens on 30–40% of real tickets.
3. **PII redaction is non-negotiable.** LLMs only ever see `[NAME_REDACTED]`, `[EMAIL_REDACTED]`, `[PHONE_REDACTED]`.
4. **RAG ensures policy consistency.** All agents read from the same FAISS index — no more conflicting policy answers across agents.
5. **HITL keeps humans in the loop.** `interrupt()` pauses the graph cleanly; `Command(resume=…)` resumes it after the human decision.


## Screenshots

<img width="1300" height="770" alt="Screenshot 2026-06-04 at 8 59 09 PM" src="https://github.com/user-attachments/assets/67e2e189-0dae-4803-b9c7-6846bc0845ed" />

<img width="1059" height="736" alt="Screenshot 2026-06-04 at 9 26 27 PM" src="https://github.com/user-attachments/assets/798248f2-1def-46f8-b4f7-954f451e7c0c" />

<img width="1077" height="711" alt="Screenshot 2026-06-04 at 9 26 48 PM" src="https://github.com/user-attachments/assets/42c90560-0b0f-400f-8616-34d6792c1c33" />

<img width="1073" height="672" alt="Screenshot 2026-06-04 at 9 27 08 PM" src="https://github.com/user-attachments/assets/3723ecc0-6252-4b7e-bc17-da3b58028788" />

<img width="1068" height="556" alt="Screenshot 2026-06-04 at 9 27 29 PM" src="https://github.com/user-attachments/assets/c0125ea4-83d0-495f-945b-2d1a91c6d797" />

<img width="1074" height="546" alt="Screenshot 2026-06-04 at 9 27 40 PM" src="https://github.com/user-attachments/assets/5954744f-dad8-46c3-9175-bf778a777cf6" />

<img width="1068" height="709" alt="Screenshot 2026-06-04 at 9 28 03 PM" src="https://github.com/user-attachments/assets/247d53cd-c023-46cf-b91b-a7f75cf2272c" />

<img width="938" height="707" alt="Screenshot 2026-06-04 at 9 28 15 PM" src="https://github.com/user-attachments/assets/71819221-8ef2-4cc7-8727-75cea345d9c9" />

<img width="964" height="710" alt="Screenshot 2026-06-04 at 9 28 40 PM" src="https://github.com/user-attachments/assets/c9bb2c8d-90b4-4c95-bb5f-9bf4e4bf43f9" />

<img width="1425" height="461" alt="Screenshot 2026-06-05 at 7 11 25 AM" src="https://github.com/user-attachments/assets/d49960d5-a720-4440-a8e7-7e40db5aacf3" />
