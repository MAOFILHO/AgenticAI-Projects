# Agentic AI - 10 Protocols Benchmark

A fork of the **ShopSmart Customer Support Multi-Agent System** that benchmarks **10 inter-service communication protocols** (REST, GraphQL, gRPC, Webhook, WebSocket, MQTT, AMQP, SOAP, MCP, A2A) side by side — using the *same* agent tool-calling loop, the *same* customer support domain, and the *same* observability stack (LangSmith + Langfuse), so results are directly comparable.

The differentiator vs. a synthetic protocol benchmark: each protocol does **real work** inside an actual ShopSmart specialist agent's tool-calling loop (e.g. GraphQL powers a product catalog search, AMQP powers a billing fraud/audit check, A2A powers a real agent-to-agent order lookup delegation) — not an isolated request/response microbenchmark. See [Protocol Comparison](#protocol-comparison) for real measured results, and [Benchmark Baselines](#benchmark-baselines) for how to reproduce them.

Everything below this point documents the underlying ShopSmart multi-agent system on which this benchmark is built.

## The Problem
ShopSmart is a mid-size e-commerce platform processing **50,000** customer support tickets per day. Their current system is a simple router that classifies tickets and sends them to human agents. This approach has several limitations:

| Current Pain Point  | Impact |
|---------------------|--------|
| Human agents handle ALL tickets |	High cost, slow response times |
| No automated order lookups | Agents spend 40% of their time just looking up order status |
| No policy consistency	| Different agents give different answers about return policies |
| Platinum customers wait in the queue | VIP customers get the same treatment as everyone else |
| No conversation memory | Customers repeat themselves when they call back |



## The Solution: Multi-Agent System
A production-grade multi-agent customer support system built with **LangChain**, **LangGraph**, and 10 protocols for Benchmark.


## Agentic Patterns Implemented

1. **Supervisor Router** — Structured output classification with business rule overrides
2. **Specialist Sub-Agents** — Domain-specific tool-calling agents via `create_agent`
3. **Deterministic Quick-Answer** — No LLM for simple order lookups (~30-40% of tickets)
4. **RAG Policy Lookup** — FAISS semantic search across policies.md
5. **PII Redaction** — Regex (email, phone) + database (names) before LLM exposure
6. **HITL Escalation** — LangGraph `interrupt()` + `Command(resume=...)` for human review
7. **Thread Memory** — `MemorySaver` for multi-turn conversation continuity
8. **Cross-Session Store** — `InMemoryStore` for customer history across threads
9. **10 Communication Protocols** — MCP-first architecture: tools defined in `mcp_server.py`, accessed via `mcp_client.py`. Google A2A spec (Agent Cards, Task lifecycle, Registry) — used for real handler-to-handler delegation. REST, GraphQL, gRPC (Phase 1), Webhook, WebSocket (Phase 2), MQTT, AMQP via Docker brokers (Phase 3), SOAP (Phase 4) — each wired into a real specialist agent's tool-calling loop and instrumented with the same shared fault-injection/timing seam (`fault_injector.py`, `protocol_timing.py`). All 10 protocols are directly comparable via `make benchmark` or the Streamlit "🔌 Protocol Benchmark" tab
10. **Dual Observability** — LangSmith auto-tracing + Langfuse callbacks


## Results & Impact
These estimates are grounded in real-world results from companies using AI support automation (e.g., Intercom, Zendesk AI, Klarna AI assistant, and IBM Watson Assistant case studies):

- **30–50%** ticket automation is typical once LLM + workflow routing is introduced.
- **25–60%** reduction in support costs via automation + deflection.
- **30–40%** of tickets are simple queries (order status, FAQs) → ideal for deterministic handling.
- **20–35%** improvement in first-response time with AI triage and prioritization.
- **15–25%** CSAT increase when memory + faster responses are introduced.
- **70%+** reduction in policy inconsistency when using centralized knowledge (RAG).


## Architecture

### Mermaid Diagram

```mermaid
graph TD
    A["🎫 Customer Ticket"] --> B["🔒 PII Redaction<br/><i>regex + database-driven</i>"]
    B --> C["🧠 Supervisor Router Node<br/><i>gpt-5-mini + Structured Output</i><br/><i>TicketClassification Pydantic model</i>"]

    C -->|"needs_escalation = true"| D["🚨 HITL Escalation Node<br/><i>interrupt() / Command(resume=...)</i>"]
    C -->|"order_status + ORD-xxxxx"| E["⚡ Quick Answer Node<br/><i>Deterministic lookup — no LLM</i>"]
    C -->|"returns"| F["📦 Returns Handler<br/><i>Returns Specialist Agent</i>"]
    C -->|"billing"| G["💳 Billing Handler<br/><i>Billing Specialist Agent</i>"]
    C -->|"product_inquiry"| H["🔍 Product Handler<br/><i>Product Specialist Agent</i>"]
    C -->|"order_status / technical"| I["📋 Order Handler<br/><i>Order Specialist Agent</i>"]

    D --> J["✉️ Response Formatter<br/><i>gpt-4.1-mini (temp=0.3)</i>"]
    E --> J
    F --> J
    G --> J
    H --> J
    I --> J

    J --> K["🔓 PII Restoration"]
    K --> L["📨 Final Customer Response"]

    subgraph MCP["MCP Protocol — 10 Original Domain Tools"]
        T1["lookup_customer"]
        T2["lookup_order"]
        T3["search_orders_by_customer"]
        T4["check_return_eligibility"]
        T5["lookup_product"]
        T6["search_products"]
        T7["policy_lookup<br/><i>RAG-backed</i>"]
        T8["calculate_refund"]
        T9["check_billing_status"]
        T10["escalate_to_manager"]
    end

    subgraph PROTO["Protocol Benchmark — 10 More Tools, 8 Protocols"]
        P1["lookup_order_rest (REST)<br/><i>order_specialist</i>"]
        P2["get_live_tracking_ws (WebSocket)<br/><i>order_specialist</i>"]
        P3["search_products_graphql (GraphQL)<br/><i>product_specialist</i>"]
        P4["get_price_grpc (gRPC)<br/><i>product_specialist</i>"]
        P5["check_stock_alert_mqtt (MQTT)<br/><i>product_specialist</i>"]
        P6["get_legacy_sku_info_soap (SOAP)<br/><i>product_specialist</i>"]
        P7["notify_shipping_partner_webhook (Webhook)<br/><i>returns_specialist</i>"]
        P8["lookup_order_via_a2a (A2A)<br/><i>returns_specialist</i>"]
        P9["audit_customer_billing_amqp (AMQP)<br/><i>billing_specialist</i>"]
        P10["lookup_customer_via_mcp_benchmark (MCP)<br/><i>billing_specialist</i>"]
    end

    subgraph RAG["RAG Knowledge Base"]
        R1["policies.md"] --> R2["RecursiveCharacterTextSplitter<br/><i>chunk_size=500, overlap=50</i>"]
        R2 --> R3["FAISS Vector Store<br/><i>text-embedding-3-small</i>"]
        R3 --> T7
    end

    subgraph MEM["Memory Layer"]
        M1["MemorySaver<br/><i>Thread-level conversation</i>"]
        M2["InMemoryStore<br/><i>Cross-session customer history</i>"]
    end

    subgraph OBS["Observability — Enabled by Default"]
        O1["LangSmith<br/><i>Auto-tracing</i>"]
        O2["Langfuse<br/><i>CallbackHandler</i>"]
        O3["Custom Scoring<br/><i>Routing accuracy</i>"]
        O4["Metrics Dashboard<br/><i>Latency, throughput, accuracy</i>"]
    end

    subgraph A2A["A2A Protocol — Google Spec"]
        A2A1["Agent Cards<br/><i>/.well-known/agent.json</i>"]
        A2A2["Task Lifecycle<br/><i>submitted → working → completed</i>"]
        A2A3["A2ARegistry<br/><i>Agent discovery</i>"]
    end

    F -.->|"A2A Task"| I
    G -.->|"A2A Task"| I

    I -.-> MCP
    F -.-> MCP
    G -.-> MCP
    H -.-> MCP

    I -.-> PROTO
    F -.-> PROTO
    G -.-> PROTO
    H -.-> PROTO
```


## LangGraph Diagram

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	supervisor(supervisor)
	quick_answer(quick_answer)
	order_handler(order_handler)
	returns_handler(returns_handler)
	billing_handler(billing_handler)
	product_handler(product_handler)
	escalation(escalation)
	format_response(format_response)
	__end__([<p>__end__</p>]):::last
	__start__ --> supervisor;
	billing_handler --> format_response;
	escalation --> format_response;
	order_handler --> format_response;
	product_handler --> format_response;
	quick_answer --> format_response;
	returns_handler --> format_response;
	supervisor -.-> billing_handler;
	supervisor -.-> escalation;
	supervisor -.-> order_handler;
	supervisor -.-> product_handler;
	supervisor -.-> quick_answer;
	supervisor -.-> returns_handler;
	format_response --> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc

```

## Why This Architecture?
- Not every path needs AI: Simple order status queries use deterministic lookups (fast, cheap, reliable)
- Specialists outperform generalists: Each sub-agent has focused tools and prompts
- Humans stay in the loop: Critical decisions still go to human managers
- RAG ensures consistency: All agents reference the same policy knowledge base


### System Summary

| Component | Details |
|-----------|---------|
| **Graph Nodes** | 8 (supervisor + 5 handlers + escalation + formatter) |
| **Specialist Agents** | 4 (order, returns, billing, product) |
| **Tools** | 20 (defined in mcp_server.py, bridged via mcp_client.py — 10 original domain tools + 10 protocol-benchmark tools) |
| **Primary LLM** | gpt-5-mini (supervisor + specialists) |
| **Secondary LLM** | gpt-4.1-mini (response formatter, temp=0.3) |
| **RAG** | FAISS + text-embedding-3-small (policies.md, top-3) |
| **Memory** | MemorySaver (thread) + InMemoryStore (cross-session) |
| **Protocols Benchmarked** | 10 — REST, GraphQL, gRPC, Webhook, WebSocket, MQTT, AMQP, SOAP, MCP, A2A |
| **Observability** | LangSmith (auto-trace) + Langfuse (callback) |
| **Frontend** | Streamlit (chat, manager review, dashboard, Protocol Benchmark tab, observability) |


### Data

| Dataset | Records | Purpose |
|---------|---------|---------|
| customers.json | 10 | Customer profiles (tier, join date, ticket history) |
| orders.json | 100 | Order catalog (status, items, tracking, delivery) |
| products.json | 20 | Product specs, pricing, stock, FAQ |
| tickets.json | 100 | Support tickets (6 categories, 4 priority levels) |
| policies.md | ~3KB | Return, shipping, billing, escalation policies (RAG source) |

### Routing Logic

```
if needs_escalation → escalation (HITL)
elif order_status + has_order_id → quick_answer (no LLM)
elif order_status (no ID) → order_handler
elif returns → returns_handler
elif billing → billing_handler
elif product_inquiry → product_handler
elif technical → order_handler
elif escalation → escalation (HITL)
else → order_handler (fallback)
```

### Escalation Triggers

- Platinum customer + high/critical priority
- Classification confidence < 0.6
- Category classified as "escalation"
- Customer explicitly requests the manager
- Legal threats or social media threats
- High-value disputes > $500


## MCP-First Tool Architecture

MCP (Model Context Protocol) is the **standard** for tool access in this project, not an add-on:

```
  mcp_server.py           mcp_client.py            agents.py
┌───────────-───┐      ┌────-─────────--─┐      ┌──────────────┐
│  FastMCP      │      │  LangChain      │      │  Specialist  │
│  10 @mcp.tool │◄─────│  StructuredTool │◄─────│  Agents      │
│  definitions  │      │  wrappers       │      │  (4 agents)  │
└──────┬─────-──┘      └──────────────---┘      └──────────────┘
       │
       ▼ (make mcp)
  External MCP Clients
  (Claude Desktop, Cursor, etc.)
```

- **`mcp_server.py`** — Single source of truth. All 10 tools are defined here with `@mcp.tool()`.
- **`mcp_client.py`** — Bridges MCP tools to LangChain `StructuredTool` objects for agent consumption.
- **`make mcp`** — Starts the MCP server standalone for external clients (stdio transport).


## Prerequisites

- **Python 3.12** (tested on 3.12.10; setup script enforces 3.12)
- **OpenAI API key** (required for LLM and embeddings)
- **LangSmith API key** (optional — enables auto-tracing; the system runs fine without it, see Troubleshooting)
- **Langfuse API keys** (optional — enables callback tracing; the system runs fine without it, see Troubleshooting)
- **Docker Desktop** (only needed for the protocol benchmark's MQTT/AMQP brokers — Mosquitto + RabbitMQ, via `docker-compose.yml`; not required for the core ShopSmart chat/graph functionality)
- **Local ports 8001-8006** free (REST, GraphQL, gRPC, Webhook, WebSocket, SOAP protocol servers started by `make protocols-up`), plus **1883** (MQTT) and **5672**/**15672** (AMQP/RabbitMQ management) if running the full protocol benchmark

<img width="901" height="77" alt="Screenshot 2026-06-19 at 11 48 46 PM" src="https://github.com/user-attachments/assets/0984914a-2ffd-4fbb-85c5-e39e528cd696" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="820" height="406" alt="Screenshot 2026-06-19 at 11 07 23 PM" src="https://github.com/user-attachments/assets/cfaaf2f4-23cb-4ea9-ba86-5414b05a92fa" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="782" height="708" alt="Screenshot 2026-07-06 at 1 52 39 PM" src="https://github.com/user-attachments/assets/0052bc93-8772-4d3c-a3c3-db3ddeaa7259" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="716" height="529" alt="Screenshot 2026-07-06 at 1 53 02 PM" src="https://github.com/user-attachments/assets/016b1573-17cb-42ef-991b-00b69ecdebae" />


## Quick Start

```bash
# 1. Automated setup
make setup

# 2. Configure API keys
#    Edit .env with your OPENAI_API_KEY (required)
#    Optionally add LANGSMITH_API_KEY, LANGFUSE keys

# 3. Run smoke tests (offline — no API key needed)
make smoke

# 4. Run full test suite (requires OPENAI_API_KEY)
make test

# 5. Process a ticket via CLI
make run

# 6. Start the MCP server
make mcp

# 7. Launch the Streamlit app
make app

# 8. Generate the graph diagram (standalone)
make diagram
# Auto-generated on every make run / make app as well
# Output: docs/graph_diagram.md (Mermaid) + docs/graph_diagram.png (image)

# 9. Start the protocol servers (REST/GraphQL/gRPC/Webhook/WebSocket/SOAP)
make protocols-up

# 10. Start the MQTT/AMQP brokers (Docker) + responders
make brokers-up
make responders-up

# 11. Run the 10-protocol benchmark (terminal summary + output/protocol_benchmark_report.json + output/protocol_comparison.png)
make benchmark
# Or use the "🔌 Protocol Benchmark" tab in the Streamlit app (make app) for the same
# run with live charts in the browser

# 12. Tear down the protocol infrastructure when done
make protocols-down
make responders-down
make brokers-down
```

<img width="1040" height="378" alt="Screenshot 2026-06-19 at 11 53 06 PM" src="https://github.com/user-attachments/assets/775f44f6-076d-472c-9289-ad0fff04520a" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="901" height="77" alt="Screenshot 2026-06-19 at 11 48 46 PM" src="https://github.com/user-attachments/assets/67256e89-2bcc-4560-8bc0-d75ffe6b1d7a" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1079" height="645" alt="Screenshot 2026-06-19 at 8 09 29 PM" src="https://github.com/user-attachments/assets/8aa778fb-acd1-4c89-8264-9e64d317084d" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1079" height="648" alt="Screenshot 2026-06-19 at 8 10 10 PM" src="https://github.com/user-attachments/assets/edc72c92-6506-4163-91ed-3db6595506ff" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1066" height="642" alt="Screenshot 2026-06-19 at 8 22 30 PM" src="https://github.com/user-attachments/assets/84df3f8f-b9aa-4722-ae07-c89f55bf3eb2" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1069" height="636" alt="Screenshot 2026-06-19 at 8 23 18 PM" src="https://github.com/user-attachments/assets/90f93db5-b757-45ad-a1e6-569766b2f1c0" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1072" height="718" alt="Screenshot 2026-06-19 at 11 32 02 PM" src="https://github.com/user-attachments/assets/356d1f55-6f54-4b9e-81c3-c04ddd4a8184" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1078" height="438" alt="Screenshot 2026-06-19 at 8 24 55 PM" src="https://github.com/user-attachments/assets/8166f0bd-94d0-4831-af79-8075e4ec79e1" />


## Cleanup & Reinstall

To clean up build artifacts or do a full reinstall from scratch:

```bash
# Stop Streamlit first (Ctrl+C in the Streamlit terminal)

# Option 1: Clean caches only (keeps .venv)
make clean

# Option 2: Full cleanup (removes .venv for fresh reinstall)
make cleanup
```
<img width="1051" height="252" alt="Screenshot 2026-06-19 at 7 31 02 PM" src="https://github.com/user-attachments/assets/1684270f-c5ac-44dd-b65d-2ae02e37ffb3" />

After `make cleanup`, reinstall with:

```bash
make setup          # creates .venv and installs dependencies
# edit .env with your API keys (your .env file is preserved)
make smoke          # offline smoke tests
make test           # full test suite (requires OPENAI_API_KEY)
make run            # process a sample ticket via CLI
make app            # launch Streamlit frontend
```


## Project Structure

```
LangGraph-ShopSmart-10-Protocols-Benchmark/
├── src/shopsmart/              # Core package (the only thing that's `pip install -e`'d)
│   ├── config.py               # LLM/embeddings config + get_data_dir()/get_output_dir()
│   ├── state.py                # State schema + Pydantic models
│   ├── data_loader.py          # JSON dataset loader + select_benchmark_tickets()
│   ├── pii.py                  # PII redaction/restoration
│   ├── rag.py                  # FAISS RAG from policies.md
│   ├── mcp_server.py           # FastMCP server — canonical tool definitions (20 tools)
│   ├── mcp_client.py           # MCP-to-LangChain bridge (agents consume tools via MCP)
│   ├── agents.py               # 4 specialist agent builders
│   ├── nodes.py                # All graph node functions
│   ├── a2a.py                  # Google A2A protocol (full spec)
│   ├── graph.py                # StateGraph assembly + diagram generation + CLI
│   ├── observability.py        # LangSmith + Langfuse setup
│   ├── metrics.py              # System + protocol-benchmark metrics tracking
│   ├── charts.py                # Visualization (all output/ artifacts)
│   ├── fault_injector.py        # Per-protocol fault injection (timeout/error/malformed/refused)
│   ├── protocol_timing.py       # @timed_protocol_call — shared instrumentation seam
│   └── protocols/                # REST/GraphQL/gRPC/Webhook/WS/MQTT/AMQP/SOAP/MCP/A2A clients+servers
├── apps/                        # Entry-point scripts (consumers of the package, not part of it)
│   ├── streamlit_app.py         # Streamlit web application (chat, HITL, dashboards, benchmark tab)
│   └── benchmark_runner.py      # CLI harness for the 10-protocol benchmark
├── data/                        # Datasets (customers, orders, products, tickets, policies)
├── tests/                       # Test suite (smoke, tools, PII, RAG, routing, HITL, memory, MCP,
│                                 #   test_protocols/ for the 10 protocol integrations)
├── scripts/                     # setup.sh, smoke_test.sh — one-time/dev tooling, not app code
├── docs/                        # Architecture diagram, auto-generated graph, metrics reference
├── docker/                      # Broker configs (mosquitto.conf)
├── output/                      # Generated reports/charts (gitignored, recreated by `make clean`)
├── docker-compose.yml           # Mosquitto + RabbitMQ, for local MQTT/AMQP brokers
├── Makefile                     # Build/run commands
└── pyproject.toml               # Packaging metadata + dependencies
```

**Why this layout:** `src/shopsmart/` is the installable package — nothing outside it should ever be imported *by* it, which is what the src-layout convention guarantees (it's why `apps/streamlit_app.py` and `apps/benchmark_runner.py` sit outside `src/`, alongside `pyproject.toml` and `docker-compose.yml`: they're consumers of the package, not part of it).

## Models

| Model | Role | Temperature |
|-------|------|-------------|
| gpt-5-mini | Primary (supervisor + specialists) | default |
| gpt-4.1-mini | Secondary (response formatter) | 0.3 |
| text-embedding-3-small | RAG embeddings | — |


## Environment Variables

### Core

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `LANGSMITH_API_KEY` | No | LangSmith auto-tracing (system runs fine without it) |
| `LANGSMITH_PROJECT` | No | LangSmith project name (default: shopsmart-support) |
| `LANGFUSE_PUBLIC_KEY` | No | Langfuse callback tracing (system runs fine without it) |
| `LANGFUSE_SECRET_KEY` | No | Langfuse secret |
| `LANGFUSE_HOST` | No | Langfuse host (default: https://us.cloud.langfuse.com) |

### Protocol Benchmark 
(all optional — defaults in `.env.example` work out of the box with `make protocols-up`/`brokers-up`)

| Variable | Description |
|----------|-------------|
| `REST_BASE_URL`, `GRAPHQL_URL`, `GRPC_PRICING_ADDR` | Phase 1 protocol server addresses |
| `WEBHOOK_URL`, `WS_TRACKING_URL` | Phase 2 protocol server addresses |
| `MQTT_BROKER_HOST`/`PORT`, `AMQP_URL` | Phase 3 broker addresses (Docker: Mosquitto, RabbitMQ) |
| `SOAP_URL` | Phase 4 protocol server address |
| `FAULT_MODE_<PROTOCOL>` | Per-protocol fault injection: `none` \| `timeout` \| `error` \| `malformed` \| `refused` (e.g. `FAULT_MODE_MQTT=timeout`) |
| `<PROTOCOL>_TIMEOUT_S` | Per-protocol client timeout in seconds |
| `<PROTOCOL>_MAX_RETRIES` | Per-protocol max retry attempts on failure |


### Benchmark Baselines

Based on initial testing with a 10-ticket batch:

| Metric | Baseline |
|--------|----------|
| Routing Accuracy | ~85-95% |
| Avg Latency (quick_answer) | < 0.5s |
| Avg Latency (specialist) | 2-4s |
| Avg Latency (HITL) | Depends on human response time |
| Escalation Rate | ~10-15% (with platinum customer in dataset) |
| Quick Answer Rate | ~35% (order_status with order ID) |

### Protocol Comparison
Example run (10 tickets, category-balanced selection)

Produced via `make benchmark` (or the Streamlit "🔌 Protocol Benchmark" tab), using `select_benchmark_tickets()` to guarantee all 10 ticket categories are represented:

| Protocol | Calls | p50 (ms) | p95 (ms) | Avg Payload (B) | Error % | Retry % |
|----------|------:|---------:|---------:|-----------------:|--------:|--------:|
| A2A      | 2 | 19,459.20 | 23,367.30 | 943 | 0 | 0 |
| MQTT     | 2 | 1,013.49  | 1,017.84  | 59  | 0 | 0 |
| REST     | 3 | 36.38     | 48.99     | 370.7 | 0 | 0 |
| GRAPHQL  | 5 | 35.89     | 53.41     | 130.8 | 0 | 0 |
| WEBHOOK  | 2 | 35.20     | 42.95     | 76  | 0 | 0 |
| SOAP     | 1 | 39.83     | 39.83     | 102 | 0 | 0 |
| AMQP     | 2 | 55.05     | 58.33     | 67  | 0 | 0 |
| WS       | 3 | 6.11      | 18.69     | 146.7 | 0 | 0 |
| GRPC     | 2 | 10.33     | 23.38     | 94.5 | 0 | 0 |
| MCP      | 2 | 2.45      | 6.99      | 98.5 | 0 | 0 |

**Key takeaway — A2A is ~3 orders of magnitude slower than every other protocol**, and that's expected, not a defect: in this project's A2A implementation, `A2AServer.send_task()` synchronously invokes the target specialist's *full* `agent.invoke()` tool-calling loop — a real nested LLM round-trip — while every other protocol here is a lightweight RPC/pub-sub call against a local server or broker. A2A's "payload" is effectively another agent's reasoning process, not a wire message. MQTT is the next-slowest (~1s), reflecting the real cost of its publish/subscribe-with-correlation-id round trip over the broker, versus the sub-100ms direct-call protocols (REST/GraphQL/gRPC/SOAP/Webhook/WS/MCP).

**A2A's latency variance is dominated by nested-LLM-call risk, not the A2A transport itself.** A follow-up 15-ticket run produced `A2A p50 = 19,459 ms` but `A2A p95 = 1,304,067 ms` (~21.7 minutes) on the exact same protocol — a ~65x spread within one protocol's own results. The cause: one A2A call's nested `order_specialist.invoke()` happened to hit an OpenAI rate-limit retry storm, and since `timed_protocol_call` measures wall-clock time around the *entire* A2A call (including whatever the delegated agent does internally), that retry delay is fully absorbed into the A2A latency figure — while `error_rate`/`retry_rate` stayed at 0% (those track transport-level retries in `protocol_timing.py`, not the OpenAI SDK's own internal backoff, which happens one layer deeper inside the nested call). In other words: A2A is the one protocol here whose measured latency is only as predictable as the LLM call graph behind it, which is itself a notable finding about delegating work via A2A vs. a direct RPC/pub-sub protocol.


## 🔌 Web App - Protocol Benchmark tab

<img width="1421" height="696" alt="Screenshot 2026-07-06 at 8 01 26 AM" src="https://github.com/user-attachments/assets/82f634ac-7e64-40a9-8dd0-637bccf64561" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1070" height="647" alt="Screenshot 2026-07-06 at 10 05 33 AM" src="https://github.com/user-attachments/assets/5be6c226-6f50-4767-be10-6eaa97b395f9" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1081" height="371" alt="Screenshot 2026-07-06 at 10 05 05 AM" src="https://github.com/user-attachments/assets/995d815f-37bc-45a5-bf04-15a910b4f710" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1084" height="393" alt="Screenshot 2026-07-06 at 10 04 28 AM" src="https://github.com/user-attachments/assets/f63f0505-2648-47b2-a6c7-f5968a47ffb8" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1137" height="669" alt="Screenshot 2026-07-06 at 9 33 05 AM" src="https://github.com/user-attachments/assets/68339d77-c3d3-453b-a353-f2c24bf20ac9" />


### CLI Commands

```bash
make metrics    # Print system summary to stdout
make test       # Run full test suite (includes routing accuracy)
make smoke      # Quick validation (no API key required for offline tests)
```
<img width="1046" height="416" alt="Screenshot 2026-06-19 at 11 39 37 PM" src="https://github.com/user-attachments/assets/7a17afb3-4e9a-4fd2-8bcd-882bea056429" />

## Troubleshooting

### Tests skipped with "OPENAI_API_KEY not set"

The `.env` file is not being loaded by pytest. Verify that your `.env` file exists in the project root (not `.env.example`) and contains `OPENAI_API_KEY=sk-...`. The test suite loads it automatically via `python-dotenv` in `tests/conftest.py`.

```bash
# Verify .env exists and has the key
cat .env | grep OPENAI_API_KEY
```

### OpenAI 429 "insufficient_quota" errors

Your OpenAI API key has no credits or billing is not enabled. Go to [platform.openai.com/settings/organization/billing](https://platform.openai.com/settings/organization/billing) and add a payment method or purchase credits. The full test suite costs under $0.50.

<img width="1087" height="448" alt="Screenshot 2026-06-19 at 6 11 50 PM" src="https://github.com/user-attachments/assets/c8aa5a88-56d0-4309-838a-d5e04cff7b69" />


### ImportError: `create_tool_calling_agent` or `create_react_agent`

The LangChain agent API has changed across versions:
- `create_tool_calling_agent` was removed in `langchain` v1.3.10
- `create_react_agent` from `langgraph.prebuilt` is deprecated in favour of `langchain.agents.create_agent`

This project uses `create_agent` from `langchain.agents` with the `system_prompt=` parameter (not the older `prompt=` parameter). If you see `TypeError: create_agent() got an unexpected keyword argument 'prompt'`, change `prompt=` to `system_prompt=` in your agent builder calls.

The pinned versions in `pyproject.toml` are tested to be compatible:

```
langchain>=0.3
langchain-openai>=0.3
langgraph>=0.3
langchain-community>=0.3
```

### LangSmith 403 "Forbidden" warnings

Your `LANGSMITH_API_KEY` is invalid, expired, or associated with a different organization. Either:
- Update the key at [smith.langchain.com](https://smith.langchain.com/) → Settings → API Keys
- Or remove/comment out `LANGSMITH_API_KEY` from `.env` to disable LangSmith tracing (the system runs fine without it)

### Langfuse connection errors

Verify that both `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set in `.env`. If using Langfuse Cloud, ensure `LANGFUSE_HOST` is set to `https://us.cloud.langfuse.com` (US) or `https://cloud.langfuse.com` (EU), matching your account region.

### `langchain-community` deprecation warning

You may see: `DeprecationWarning: langchain-community is being sunset`. This is a known upstream warning — the FAISS integration still works. A future update will migrate to a standalone `langchain-faiss` package when available.

### `ModuleNotFoundError: No module named 'langchain_text_splitters'`

Run `pip install -e ".[dev]"` again — this dependency is installed transitively via `langchain`. If it persists, install directly: `pip install langchain-text-splitters`.

### macOS: Streamlit Watchdog performance warning

On macOS, Streamlit recommends the Watchdog module for better file-watching performance. This is included in the project dependencies, but requires Xcode command-line tools:

```bash
xcode-select --install   # one-time macOS setup
pip install -e ".[dev]"  # watchdog is included in dependencies
```

### Streamlit: `ImportError: cannot import name 'X' from 'shopsmart...'` after pulling/editing code

Streamlit's autoreload only re-executes `streamlit_app.py` itself on save — it does **not** reliably re-import already-loaded modules in `src/shopsmart/` within a long-running server process (this bit us when adding `select_benchmark_tickets` to `data_loader.py` while the app was already running from a prior manual test session). If you add or rename a function/module and the running app can't find it, fully restart the server rather than relying on the browser's auto-rerun:

```bash
# In the terminal running `make app`:
Ctrl+C
make app
```

### Protocol Benchmark tab: some protocols always show 0 calls

This can be a real finding, not a bug: category-to-protocol coverage isn't 1:1 (see `select_benchmark_tickets()` in `data_loader.py`, which round-robins tickets across categories precisely to make this less likely). Even with every category represented, a given protocol only fires if the LLM actually chooses that tool during its tool-calling loop for that ticket. Also note **order_status tickets with a resolvable `ORD-xxxxx` id skip the agent entirely** via the deterministic quick-answer path (see "Routing Logic" above) — so REST/WebSocket (bound to `order_specialist`) won't fire for those, only for order tickets that fall through to the full agent. Increasing ticket count improves odds; 0 calls after a reasonably sized run (8-10+ tickets) is worth noting as a real signal about tool-selection/routing behaviour.

### Python version errors

This project requires **Python 3.12** (tested on 3.12.10). The setup script enforces this — if `python3.12` is not found, it will tell you how to install it:

```bash
brew install python@3.12     # Homebrew
pyenv install 3.12.10        # pyenv
```
<img width="901" height="77" alt="Screenshot 2026-06-19 at 11 48 46 PM" src="https://github.com/user-attachments/assets/23e1b659-1335-4af8-a608-95c11526cc9d" />

If you see syntax errors related to `str | None` or `dict[str, list]`, your Python version is too old. Check with `python3.12 --version`.


## System Metrics Reference

### Operational Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **Routing Accuracy** | % of tickets correctly classified by supervisor | ≥ 80% |
| **Avg Latency** | Mean time from ticket submission to final response | < 5s |
| **Escalation Rate** | % of tickets requiring HITL human review | < 15% |
| **Quick Answer Rate** | % of tickets resolved via deterministic path (no LLM) | 30-40% |
| **Tool Usage** | Frequency of each tool invocation across tickets | — |
| **Category Distribution** | Breakdown of tickets by category | — |
| **Priority Distribution** | Breakdown of tickets by priority level | — |

<img width="1071" height="596" alt="Screenshot 2026-06-19 at 7 07 22 PM" src="https://github.com/user-attachments/assets/6459d110-34c4-4d7f-ada3-8ff5640d87d6" />


### Observability Metrics (LangSmith + Langfuse)

| Metric | Platform | Description |
|--------|----------|-------------|
| **Trace Latency** | Both | Per-node execution time breakdown |
| **Token Usage** | Both | Input/output tokens per LLM call |
| **Cost per Ticket** | Both | $ cost per ticket (auto-computed from tokens) |
| **Custom Scores** | Both | Routing accuracy score per classification |
| **Error Rate** | Both | Failed LLM calls or tool errors |

<img width="1165" height="651" alt="Screenshot 2026-06-19 at 6 38 04 PM" src="https://github.com/user-attachments/assets/e0a93de3-3dbc-44db-b466-6a816df2b0d0" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1429" height="742" alt="Screenshot 2026-06-19 at 6 38 47 PM" src="https://github.com/user-attachments/assets/3af305a1-a589-45b0-b770-a3681f2673d8" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1422" height="701" alt="Screenshot 2026-06-19 at 6 39 00 PM" src="https://github.com/user-attachments/assets/ef38336c-3316-41a6-b670-e0e43b4e3dbf" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="950" height="693" alt="Screenshot 2026-06-19 at 6 39 45 PM" src="https://github.com/user-attachments/assets/bb408ed2-f93d-40c3-8e7c-cf773b77f3e1" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1435" height="665" alt="Screenshot 2026-06-19 at 6 41 02 PM" src="https://github.com/user-attachments/assets/d23a6f56-91c1-4602-9b3c-9119b9866d22" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="859" height="665" alt="Screenshot 2026-06-19 at 6 41 48 PM" src="https://github.com/user-attachments/assets/92bb67f6-93e1-4ac3-9c26-37d6659bb2cf" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="859" height="666" alt="Screenshot 2026-06-19 at 6 41 18 PM" src="https://github.com/user-attachments/assets/ebdb165a-a899-4063-96a8-a0b177fb7420" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1116" height="519" alt="610518677-972a645c-a044-450c-a339-7fdabb6f0d95" src="https://github.com/user-attachments/assets/f685687c-4a12-44b6-98ff-d5a1adaefb40" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1116" height="553" alt="610518669-09812a34-a64f-4a55-8f08-47d83c96cd02" src="https://github.com/user-attachments/assets/70940608-363c-4ca1-bda2-a0e727e145d4" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1116" height="549" alt="610518649-0276472a-8b0c-45f0-8764-5968c73a92aa" src="https://github.com/user-attachments/assets/4c8a2e9f-ef91-429f-b762-9359fca791d4" />


## ShopSmart Web Application (screenshots)

<img width="1436" height="743" alt="Screenshot 2026-06-19 at 6 26 10 PM" src="https://github.com/user-attachments/assets/d2b6b69c-65a6-4e25-a90f-9b06f0041250" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1430" height="746" alt="Screenshot 2026-06-19 at 6 32 18 PM" src="https://github.com/user-attachments/assets/aa56d5eb-e144-4e25-9b12-ca1b0dd5eb66" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1428" height="744" alt="Screenshot 2026-06-19 at 6 36 11 PM" src="https://github.com/user-attachments/assets/5b751aa1-3413-49d5-9feb-6c9eb8849f33" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1430" height="748" alt="Screenshot 2026-06-19 at 6 36 32 PM" src="https://github.com/user-attachments/assets/18e6358a-8382-4bd4-85ba-0b7911b2241b" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1098" height="659" alt="Screenshot 2026-06-19 at 7 06 19 PM" src="https://github.com/user-attachments/assets/3707d529-f545-4d91-af1a-dfc50c13ab56" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1083" height="630" alt="Screenshot 2026-06-19 at 7 04 34 PM" src="https://github.com/user-attachments/assets/247dd5ea-0d83-421c-b7af-aedb11d4d20e" />

<img width="100%" height="1" alt="" src="https://github.com/user-attachments/assets/f2af28ee-a373-4488-89e5-2b84d5da9620" />
<br><br>
<img width="1064" height="627" alt="Screenshot 2026-06-19 at 11 45 31 PM" src="https://github.com/user-attachments/assets/e2d3e12f-9c77-4fc5-b57c-ae904cff81b0" />


## Author

**Marcos Oliveira** — [LinkedIn](https://www.linkedin.com/in/mfilho1/) | [GitHub](https://github.com/MAOFILHO)
