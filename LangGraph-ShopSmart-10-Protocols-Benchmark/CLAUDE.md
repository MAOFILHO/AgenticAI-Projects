# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make setup          # create .venv, install deps (enforces Python 3.12)
make smoke          # offline smoke tests, no API key needed
make test           # full pytest suite (requires OPENAI_API_KEY), -v --tb=short
make test-offline   # subset that doesn't need an API key (smoke, pii, tools)
make run            # process a sample ticket via CLI (python -m shopsmart.graph)
make mcp            # start the MCP server standalone (stdio transport)
make app            # launch Streamlit frontend
make metrics        # print system metrics summary (python -m shopsmart.metrics)
make diagram        # regenerate docs/graph_diagram.md + .png
make clean          # remove caches/build artifacts (keeps .venv)
make cleanup        # clean + remove .venv
```

Run a single test: `python -m pytest tests/test_routing.py -v` (or `::test_name` for one case).

Tests load `.env` automatically via `python-dotenv` in `tests/conftest.py`. If tests are skipped with "OPENAI_API_KEY not set", check `.env` exists at the project root (not just `.env.example`).

## Architecture

This is a LangGraph `StateGraph` pipeline for automated customer support ticket processing, built MCP-first with an A2A layer for inter-agent messaging.

### Request flow (`src/shopsmart/graph.py`, `nodes.py`)

```
ticket -> PII redaction -> supervisor (router) -> [quick_answer | order/returns/billing/product handler | escalation] -> format_response -> PII restoration -> reply
```

- **Supervisor** (`nodes.py`): classifies the ticket via structured output (`TicketClassification` in `state.py`) using gpt-5-mini, then applies business-rule overrides (see Escalation Triggers below) that can force a route regardless of the LLM's classification.
- **Routing** is deterministic once classification is known — see the `if/elif` chain in `docs/architecture.md` under "Routing Logic". Order-status tickets with a resolvable `ORD-xxxxx` id skip the LLM entirely and go to `quick_answer` (direct dataset lookup).
- **Specialist handlers** (order, returns, billing, product) are LangChain `create_agent` tool-calling agents (`agents.py`), each scoped to a subset of the 10 MCP tools relevant to its domain.
- **Escalation** uses `interrupt()` / `Command(resume=...)` (LangGraph HITL) — the graph pauses until a human manager resumes it; this is what backs the Streamlit "manager review" view.
- **format_response** runs a second, cheaper LLM (gpt-4.1-mini, temp=0.3) to turn the handler's raw result into a customer-facing message, then PII is restored before returning.

### MCP-first tool architecture

`mcp_server.py` is the single source of truth for all 10 tools (`@mcp.tool()` definitions: customer/order/product lookups, return eligibility, refund calculation, billing status, policy RAG lookup, escalation). `mcp_client.py` bridges these into LangChain `StructuredTool` objects that `agents.py` wires into the specialist agents — the agents never call tool logic directly. Because the server is a standalone FastMCP app, `make mcp` also exposes the same 10 tools to external MCP clients (Claude Desktop, Cursor, etc.) over stdio.

When adding or changing a tool, edit `mcp_server.py` only — `mcp_client.py`'s bridging is generic and shouldn't need per-tool changes.

### A2A protocol (`a2a.py`)

Implements the Google A2A spec (Agent Cards at `/.well-known/agent.json`, Task lifecycle `submitted -> working -> completed`, `A2ARegistry` for discovery). Used for handler-to-handler delegation (e.g. returns/billing handlers dispatching an A2A Task to the order handler for order data) rather than for the primary MCP tool path.

### PII handling (`pii.py`)

Redaction happens before the ticket text reaches any LLM (regex for email/phone, database lookup for names/other identifiers) and restoration happens after `format_response`, so **all node functions between redaction and restoration operate on redacted text** — don't assume raw PII is available inside handler/supervisor logic.

### RAG (`rag.py`)

`policies.md` is chunked (`RecursiveCharacterTextSplitter`, chunk_size=500/overlap=50), embedded with `text-embedding-3-small`, and indexed in an in-memory FAISS store. The `policy_lookup` MCP tool queries this index (top-3) — it is the only path to policy content; specialists should not hardcode policy text.

### Memory

Two distinct layers, don't conflate them: `MemorySaver` gives thread-level (single conversation) checkpointing; `InMemoryStore` gives cross-session customer history keyed off customer id, independent of thread.

### State and data

- `state.py` defines `CustomerSupportState` (the graph's TypedDict state) and `TicketClassification` (the supervisor's structured-output Pydantic model) — check this file first when tracing what data flows between nodes.
- `data_loader.py` loads the static JSON datasets in `data/` (customers, orders, products, tickets) and `policies.md`; there is no database — all lookups are in-memory against these fixtures.
- `config.py` centralizes LLM/embedding model configuration (gpt-5-mini primary, gpt-4.1-mini for formatting, text-embedding-3-small for RAG).

### Observability (`observability.py`, `metrics.py`)

LangSmith auto-tracing and a Langfuse `CallbackHandler` are both wired in by default (not opt-in) — expect traces/callbacks to fire in normal test runs if the corresponding API keys are set. `metrics.py` computes routing accuracy, latency, escalation rate, and quick-answer rate from a ticket batch; `make metrics` prints this summary, `charts.py` renders it to PNGs into `output/` (`observability_report.png`, `routing_distribution.png`, `tool_usage.png`, `protocol_comparison.png`), which `make clean` removes.

### Frontend (`apps/streamlit_app.py`)

Single Streamlit app covering chat, the HITL manager-review queue, the metrics/observability dashboard, and the Protocol Benchmark tab — it drives the same `graph.py` `build_system()` entrypoint used by the CLI, so graph changes affect both surfaces. Entry-point scripts (`apps/streamlit_app.py`, `apps/benchmark_runner.py`) live outside `src/shopsmart/` since they're consumers of the installed package, not part of it.

## Notes on dependencies

LangChain's agent-construction API has shifted across versions: this project uses `create_agent` from `langchain.agents` (not the deprecated `langgraph.prebuilt.create_react_agent` or removed `create_tool_calling_agent`), and its system prompt is passed as `system_prompt=`, not `prompt=`.
