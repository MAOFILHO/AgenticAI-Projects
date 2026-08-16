# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

This repo is **multi-context**: it's a flat collection of independent, self-contained projects (different clouds, frameworks, and domains — AWS Bedrock, Azure, LangChain, several distinct LangGraph apps), not one coherent codebase. Each top-level project directory is its own context.

## Before exploring, read these

- **`CONTEXT-MAP.md`** at the repo root — it points at one `CONTEXT.md` per context (per project directory). Read each one relevant to the topic.
- **`docs/adr/`** at the repo root — system-wide decisions (repo conventions, cross-project tooling).
- **`<project>/docs/adr/`** — decisions scoped to that one project. Check this in addition to the root ADRs when working inside a specific project directory.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily when terms or decisions actually get resolved.

## File structure

```
/
├── CONTEXT-MAP.md
├── docs/adr/                                   ← repo-wide decisions (conventions, tooling)
├── AWS-Bedrock-AgentCore-RAG-Memory-Agent/
│   ├── CONTEXT.md
│   └── docs/adr/                               ← project-scoped decisions
├── Azure-Smart-Incident-Urban-Safety-AI-v2.0/
│   ├── CONTEXT.md
│   └── docs/adr/
├── Compare-ADK-Frameworks-Bank-Compliance/
│   ├── CONTEXT.md
│   └── docs/adr/
├── LangChain-RAG-Patterns-Benchmark/
│   ├── CONTEXT.md
│   └── docs/adr/
├── LangGraph-Customer-Support-MultiAgent/
│   ├── CONTEXT.md
│   └── docs/adr/
├── LangGraph-Financial-Analyst-ReAct-RAG/
│   ├── CONTEXT.md
│   └── docs/adr/
├── LangGraph-MCP-Insurance-Claims-MultiAgent/
│   ├── CONTEXT.md
│   └── docs/adr/
├── LangGraph-RegSentinel-Compliance-AI/
│   ├── CONTEXT.md
│   └── docs/adr/
├── LangGraph-SecureLife-MCP-Chainlit-AI/
│   ├── CONTEXT.md
│   └── docs/adr/
├── LangGraph-ShopSmart-10-Protocols-Benchmark/
│   ├── CONTEXT.md
│   └── docs/adr/
└── LangGraph-ShopSmart-MCP-A2A-MultiAgent-AI-Observability/
    ├── CONTEXT.md
    └── docs/adr/
```

None of the `CONTEXT.md` / ADR files exist yet — they're created lazily, project by project, as terms or decisions actually get resolved for that project.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in that project's `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_
