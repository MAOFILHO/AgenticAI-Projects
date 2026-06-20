# ShopSmart Support — System Architecture

## Mermaid Diagram

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

    subgraph MCP["MCP Protocol — 10 Tools"]
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
```

## System Summary

| Component | Details |
|-----------|---------|
| **Graph Nodes** | 8 (supervisor + 5 handlers + escalation + formatter) |
| **Specialist Agents** | 4 (order, returns, billing, product) |
| **Tools** | 10 (MCP-first: defined in mcp_server.py, bridged via mcp_client.py) |
| **Primary LLM** | gpt-5-mini (supervisor + specialists) |
| **Secondary LLM** | gpt-4.1-mini (response formatter, temp=0.3) |
| **RAG** | FAISS + text-embedding-3-small (policies.md, top-3) |
| **Memory** | MemorySaver (thread) + InMemoryStore (cross-session) |
| **Protocols** | MCP (tool invocation) + A2A (inter-agent communication) |
| **Observability** | LangSmith (auto-trace) + Langfuse (callback) |
| **Frontend** | Streamlit (chat, manager review, dashboard, observability) |

## Patterns Implemented

1. **Supervisor Router** — Structured output classification with business rule overrides
2. **Specialist Sub-Agents** — Domain-specific tool-calling agents via `create_agent`
3. **Deterministic Quick-Answer** — No LLM for simple order lookups (~30-40% of tickets)
4. **RAG Policy Lookup** — FAISS semantic search across policies.md
5. **PII Redaction** — Regex (email, phone) + database (names) before LLM exposure
6. **HITL Escalation** — LangGraph `interrupt()` + `Command(resume=...)` for human review
7. **Thread Memory** — `MemorySaver` for multi-turn conversation continuity
8. **Cross-Session Store** — `InMemoryStore` for customer history across threads
9. **MCP Protocol** — MCP-first architecture: tools defined in `mcp_server.py`, accessed via `mcp_client.py`, also available standalone (`make mcp`)
10. **A2A Protocol** — Google A2A spec (Agent Cards, Task lifecycle, Registry)
11. **Dual Observability** — LangSmith auto-tracing + Langfuse callbacks

## Data

| Dataset | Records | Purpose |
|---------|---------|---------|
| customers.json | 10 | Customer profiles (tier, join date, ticket history) |
| orders.json | 100 | Order catalog (status, items, tracking, delivery) |
| products.json | 20 | Product specs, pricing, stock, FAQ |
| tickets.json | 100 | Support tickets (6 categories, 4 priority levels) |
| policies.md | ~3KB | Return, shipping, billing, escalation policies (RAG source) |

## Routing Logic

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

## Escalation Triggers

- Platinum customer + high/critical priority
- Classification confidence < 0.6
- Category classified as "escalation"
- Customer explicitly requests manager
- Legal threats or social media threats
- High-value disputes > $500
