"""Generate the final ADK comparison report and metrics table."""
import os
from shared.metrics import RunMetrics

ADK_DESCRIPTIONS = {
    "LangGraph": {
        "orchestration": "Graph (nodes + edges, fan-out with Send)",
        "control": "Maximum — every path explicit",
        "state": "Explicit TypedDict (ComplianceState)",
        "strengths": "Deterministic routing, HITL interrupt, MemorySaver checkpoints",
        "best_for": "Complex enterprise workflows, compliance, auditable paths",
    },
    "OpenAI Agent SDK": {
        "orchestration": "Handoff-based (triage → specialist agents)",
        "control": "Medium — LLM decides when to hand off",
        "state": "Implicit conversation history",
        "strengths": "Built-in guardrails, SQLiteSession memory, OpenAI tracing dashboard",
        "best_for": "OpenAI-native apps, voice (RealtimeAgent), fast iteration",
    },
    "CrewAI": {
        "orchestration": "Role-based sequential (Researcher → Analyst → Writer)",
        "control": "Medium — process type (sequential/hierarchical) decides order",
        "state": "Task context chain (output flows to next task)",
        "strengths": "Natural role/goal/backstory pattern, good for creative/content workflows",
        "best_for": "Content pipelines, research teams, editorial workflows",
    },
    "AutoGen": {
        "orchestration": "Group chat — RoundRobin (fixed turn order)",
        "control": "Minimal — agents self-organize through conversation",
        "state": "Chat message history",
        "strengths": "Natural multi-agent debate, SelectorGroupChat for dynamic routing",
        "best_for": "Research, competitive analysis, brainstorming, debate scenarios",
    },
    "Google ADK": {
        "orchestration": "Structured: ParallelAgent → SequentialAgent → LoopAgent",
        "control": "High — pipeline structure is explicit, loop has max_iterations",
        "state": "Session state (key/value via output_key)",
        "strengths": "Native GCP integration, built-in quality review loop, LiteLLM flexibility",
        "best_for": "Google Cloud workloads, Gemini models, structured pipelines with retry",
    },
}


def print_comparison(results: list[tuple[RunMetrics, str]]) -> None:
    print("\n")
    print("=" * 70)
    print("  ADK FRAMEWORKS COMPARISON — MIDWESTBANK COMPLIANCE PIPELINE")
    print("=" * 70)

    print(f"\n{'Framework':<22} {'Status':<10} {'Time(s)':<10} {'LLM Calls':<12} {'Report Words':<14}")
    print("-" * 70)
    for m, _ in results:
        print(f"{m.framework:<22} {m.status:<10} {m.elapsed_seconds:<10} {m.llm_calls:<12} {m.report_word_count:<14}")

    print("\n")
    print("=" * 70)
    print("  ARCHITECTURAL COMPARISON")
    print("=" * 70)

    for m, _ in results:
        desc = ADK_DESCRIPTIONS.get(m.framework, {})
        print(f"\n  [{m.framework}]")
        print(f"    Orchestration : {desc.get('orchestration', 'N/A')}")
        print(f"    Control Level : {desc.get('control', 'N/A')}")
        print(f"    State Mgmt    : {desc.get('state', 'N/A')}")
        print(f"    Strengths     : {desc.get('strengths', 'N/A')}")
        print(f"    Best For      : {desc.get('best_for', 'N/A')}")

    print("\n")
    print("=" * 70)
    print("  KEY DIFFERENCES SUMMARY")
    print("=" * 70)
    print("""
  LangGraph     → Maximum control. You define every node and edge. Best when you
                  need deterministic, auditable, compliance-grade routing.

  OpenAI SDK    → Convention over configuration. Fast to build. LLM decides
                  handoffs. Best for OpenAI-native apps with voice support.

  CrewAI        → Team metaphor. Agents have roles, goals, backstories. Sequential
                  or hierarchical task flow. Best for content/creative pipelines.

  AutoGen       → Conversation as orchestration. Agents debate in group chat.
                  RoundRobin or LLM-selected speakers. Best for analysis/research.

  Google ADK    → Pipeline primitives: ParallelAgent, SequentialAgent, LoopAgent.
                  Explicit structure meets GCP-native tooling and Gemini models.

  DECISION GUIDE:
    Deterministic routing + compliance?   → LangGraph
    OpenAI ecosystem + voice?             → OpenAI Agents SDK
    Content/creative team workflow?       → CrewAI
    Multi-agent debate + research?        → AutoGen
    Google Cloud + Gemini + pipelines?    → Google ADK
""")
    if os.getenv("LANGCHAIN_API_KEY"):
        project = os.getenv("LANGCHAIN_PROJECT", "compare-adks")
        print(f"  LangSmith traces  → https://smith.langchain.com/projects/{project}")
        print()
