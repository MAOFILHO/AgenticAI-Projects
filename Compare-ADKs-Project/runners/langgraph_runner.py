"""LangGraph runner — graph-based orchestration with fan-out workers and HITL."""
import json
import operator
import os
from typing import TypedDict, Annotated, Literal

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from pydantic import BaseModel, Field

from shared.metrics import RunMetrics
from shared.tools import (
    get_transaction_stats,
    get_sar_status,
    get_kyc_stats,
    detect_aml_patterns,
    get_risk_summary,
)

FRAMEWORK = "LangGraph"
TASK_PROMPT = (
    "Generate a concise AML compliance section for MidwestBank's FinCEN report. "
    "Use the provided data summary to write a professional, factual compliance section "
    "covering the key findings. Be specific with numbers. 150-200 words."
)

SECTION_TOPICS = [
    {"id": "aml_transactions", "topic": "AML Transaction Monitoring", "tool": "transaction_stats"},
    {"id": "sar_filings",      "topic": "SAR Filing Status",           "tool": "sar_status"},
    {"id": "kyc_cdd",          "topic": "KYC/CDD Compliance",          "tool": "kyc_stats"},
    {"id": "aml_patterns",     "topic": "AML Pattern Detection",       "tool": "aml_patterns"},
    {"id": "risk_summary",     "topic": "Risk Indicators Summary",     "tool": "risk_summary"},
]


class SectionDraft(TypedDict):
    section_id: str
    topic: str
    content: str


class ComplianceState(TypedDict):
    report_type: str
    planned_sections: list[dict]
    section_drafts: Annotated[list[SectionDraft], operator.add]
    full_report: str


def orchestrator_node(state: ComplianceState) -> dict:
    return {"planned_sections": SECTION_TOPICS}


def assign_workers(state: ComplianceState) -> list[Send]:
    return [
        Send("worker_node", {"section": s, "report_type": state["report_type"]})
        for s in state["planned_sections"]
    ]


TOOL_MAP = {
    "transaction_stats": get_transaction_stats,
    "sar_status": get_sar_status,
    "kyc_stats": get_kyc_stats,
    "aml_patterns": detect_aml_patterns,
    "risk_summary": get_risk_summary,
}


def worker_node(state: dict) -> dict:
    section = state["section"]
    tool_fn = TOOL_MAP[section["tool"]]
    data = tool_fn()

    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.1)
    messages = [
        SystemMessage(content="You are an AML compliance report writer for a mid-size U.S. bank."),
        HumanMessage(content=f"Write the '{section['topic']}' section.\n\nData:\n{data}\n\n{TASK_PROMPT}"),
    ]
    result = llm.invoke(messages)
    return {
        "section_drafts": [{
            "section_id": section["id"],
            "topic": section["topic"],
            "content": result.content,
        }]
    }


def synthesis_node(state: ComplianceState) -> dict:
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.1)
    sections_text = "\n\n".join(
        f"## {d['topic']}\n{d['content']}" for d in state["section_drafts"]
    )
    messages = [
        SystemMessage(content="You are a senior compliance officer synthesizing a regulatory report."),
        HumanMessage(content=(
            f"Synthesize these compliance sections into a final {state['report_type']} report "
            f"with an Executive Summary.\n\n{sections_text}"
        )),
    ]
    result = llm.invoke(messages)
    return {"full_report": result.content}


def build_graph():
    builder = StateGraph(ComplianceState)
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("worker_node", worker_node)
    builder.add_node("synthesis", synthesis_node)

    builder.add_edge(START, "orchestrator")
    builder.add_conditional_edges("orchestrator", assign_workers, ["worker_node"])
    builder.add_edge("worker_node", "synthesis")
    builder.add_edge("synthesis", END)

    return builder.compile(checkpointer=MemorySaver())


def run(metrics: RunMetrics) -> str:
    print(f"\n{'='*60}")
    print(f"  Now running the pipeline using {FRAMEWORK}")
    print(f"{'='*60}")

    graph = build_graph()
    thread_config = {"configurable": {"thread_id": "midwest-fincen-q4"}}

    result = graph.invoke(
        {"report_type": "FinCEN", "planned_sections": [], "section_drafts": [], "full_report": ""},
        config=thread_config,
    )
    metrics.tool_calls = len(SECTION_TOPICS)
    metrics.llm_calls = len(SECTION_TOPICS) + 1  # workers + synthesis

    report = result.get("full_report", "")
    print(f"\n[{FRAMEWORK}] Report generated ({len(report.split())} words)")
    print(f"\n{report[:800]}{'...' if len(report) > 800 else ''}")
    return report
