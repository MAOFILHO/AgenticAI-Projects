# ShopSmart Customer Support — Multi-Agent System

A production-grade multi-agent customer support system built with **LangChain**, **LangGraph**, **MCP**, and **A2A** protocols.

## Prerequisites

- **Python 3.12** (tested on 3.12.10; setup script enforces 3.12)
- **OpenAI API key** (required for LLM and embeddings)
- **LangSmith API key** (optional — observability)
- **Langfuse API keys** (optional — observability)

## Architecture

- **Supervisor Router** — gpt-5-mini with structured output classification
- **4 Specialist Sub-Agents** — Order, Returns, Billing, Product
- **HITL Escalation** — Human-in-the-loop with interrupt/resume
- **RAG** — FAISS vector store over policies.md
- **10 MCP Tools** — MCP-first architecture (all tools defined and accessed via MCP)
- **A2A Protocol** — Google A2A spec for inter-agent communication
- **Observability** — LangSmith + Langfuse (enabled by default)
- **Streamlit Frontend** — Chat, manager review, dashboard, observability

See [docs/architecture.md](docs/architecture.md) for the hand-crafted system diagram and [docs/graph_diagram.md](docs/graph_diagram.md) for the auto-generated LangGraph diagram.

### MCP-First Tool Architecture

MCP (Model Context Protocol) is the **standard** for tool access in this project, not an add-on:

```
mcp_server.py          mcp_client.py           agents.py
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
```

## Cleanup & Reinstall

To clean up build artifacts or do a full reinstall from scratch:

```bash
# Stop Streamlit first (Ctrl+C in the Streamlit terminal)

# Option 1: Clean caches only (keeps .venv)
make clean

# Option 2: Full cleanup (removes .venv for fresh reinstall)
make cleanup
```

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
shopsmart-support/
├── src/shopsmart/          # Core package
│   ├── config.py           # LLM + embeddings configuration
│   ├── state.py            # State schema + Pydantic models
│   ├── data_loader.py      # JSON dataset loader
│   ├── pii.py              # PII redaction/restoration
│   ├── rag.py              # FAISS RAG from policies.md
│   ├── mcp_server.py       # FastMCP server — canonical tool definitions (10 tools)
│   ├── mcp_client.py       # MCP-to-LangChain bridge (agents consume tools via MCP)
│   ├── agents.py           # 4 specialist agent builders
│   ├── nodes.py            # All graph node functions
│   ├── a2a.py              # Google A2A protocol (full spec)
│   ├── graph.py            # StateGraph assembly + diagram generation + CLI
│   ├── observability.py    # LangSmith + Langfuse setup
│   ├── metrics.py          # System metrics tracking
│   └── charts.py           # Visualization
├── data/                   # Datasets (customers, orders, products, tickets, policies)
├── tests/                  # Test suite (smoke, tools, PII, RAG, routing, HITL, memory, MCP)
├── scripts/                # setup.sh, smoke_test.sh
├── docs/                   # Architecture diagram, auto-generated graph, metrics reference
├── streamlit_app.py        # Streamlit web application
├── Makefile                # Build commands
└── pyproject.toml          # Dependencies
```

## Models

| Model | Role | Temperature |
|-------|------|-------------|
| gpt-5-mini | Primary (supervisor + specialists) | default |
| gpt-4.1-mini | Secondary (response formatter) | 0.3 |
| text-embedding-3-small | RAG embeddings | — |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `LANGSMITH_API_KEY` | No | LangSmith auto-tracing |
| `LANGSMITH_PROJECT` | No | LangSmith project name (default: shopsmart-support) |
| `LANGFUSE_PUBLIC_KEY` | No | Langfuse callback tracing |
| `LANGFUSE_SECRET_KEY` | No | Langfuse secret |
| `LANGFUSE_HOST` | No | Langfuse host (default: https://us.cloud.langfuse.com) |

## Troubleshooting

### Tests skipped with "OPENAI_API_KEY not set"

The `.env` file is not being loaded by pytest. Verify that your `.env` file exists in the project root (not `.env.example`) and contains `OPENAI_API_KEY=sk-...`. The test suite loads it automatically via `python-dotenv` in `tests/conftest.py`.

```bash
# Verify .env exists and has the key
cat .env | grep OPENAI_API_KEY
```

### OpenAI 429 "insufficient_quota" errors

Your OpenAI API key has no credits or billing is not enabled. Go to [platform.openai.com/settings/organization/billing](https://platform.openai.com/settings/organization/billing) and add a payment method or purchase credits. The full test suite costs under $0.50.

### ImportError: `create_tool_calling_agent` or `create_react_agent`

The LangChain agent API has changed across versions:
- `create_tool_calling_agent` was removed in `langchain` v1.3.10
- `create_react_agent` from `langgraph.prebuilt` is deprecated in favor of `langchain.agents.create_agent`

This project uses `create_agent` from `langchain.agents` with the `system_prompt=` parameter (not the older `prompt=` parameter). If you see `TypeError: create_agent() got an unexpected keyword argument 'prompt'`, change `prompt=` to `system_prompt=` in your agent builder calls.

The pinned versions in `pyproject.toml` are tested compatible:

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

Verify that both `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set in `.env`. If using Langfuse Cloud, ensure `LANGFUSE_HOST` is set to `https://us.cloud.langfuse.com` (US) or `https://cloud.langfuse.com` (EU) matching your account region.

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

### Python version errors

This project requires **Python 3.12** (tested on 3.12.10). The setup script enforces this — if `python3.12` is not found, it will tell you how to install it:

```bash
brew install python@3.12     # Homebrew
pyenv install 3.12.10        # pyenv
```

If you see syntax errors related to `str | None` or `dict[str, list]`, your Python version is too old. Check with `python3.12 --version`.
