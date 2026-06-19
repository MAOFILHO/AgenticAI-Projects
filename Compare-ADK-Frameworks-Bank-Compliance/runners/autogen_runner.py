"""AutoGen runner — conversation-based group chat orchestration."""
import asyncio
import json
import os

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

from shared.metrics import RunMetrics
from shared.tools import (
    detect_aml_patterns,
    get_kyc_stats,
    get_risk_summary,
    get_sar_status,
    get_transaction_stats,
)

FRAMEWORK = "AutoGen"


def _get_model_client():
    return OpenAIChatCompletionClient(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.environ["OPENAI_API_KEY"],
    )


def _build_data_context() -> str:
    """Pre-fetch all data so agents can reason from context without tool calls."""
    return (
        f"TRANSACTION STATS:\n{get_transaction_stats()}\n\n"
        f"SAR STATUS:\n{get_sar_status()}\n\n"
        f"KYC STATS:\n{get_kyc_stats()}\n\n"
        f"AML PATTERNS:\n{detect_aml_patterns()}\n\n"
        f"RISK SUMMARY:\n{get_risk_summary()}"
    )


async def _run_async(metrics: RunMetrics) -> str:
    model_client = _get_model_client()
    data_context = _build_data_context()
    metrics.tool_calls = 5

    data_analyst = AssistantAgent(
        name="Data_Analyst",
        model_client=model_client,
        system_message=(
            "You are MidwestBank's BSA/AML data analyst. "
            "You have access to the following compliance data:\n\n"
            f"{data_context}\n\n"
            "In the group discussion, provide a data-driven summary of the key "
            "findings: suspicious transaction counts, SAR filing backlog, "
            "KYC deficiency numbers, and AML patterns detected. "
            "Be specific with numbers. 3-5 bullet points."
        ),
    )

    compliance_analyst = AssistantAgent(
        name="Compliance_Analyst",
        model_client=model_client,
        system_message=(
            "You are MidwestBank's compliance risk analyst. "
            "You have access to the following compliance data:\n\n"
            f"{data_context}\n\n"
            "In the group discussion, assess the regulatory risk: "
            "which findings require immediate SAR filing, which KYC gaps pose "
            "BSA violations, and what enhanced due diligence is needed for "
            "high-risk/PEP customers. Provide risk severity ratings. 3-5 bullet points."
        ),
    )

    report_writer = AssistantAgent(
        name="Report_Writer",
        model_client=model_client,
        system_message=(
            "You are MidwestBank's senior compliance report writer. "
            "Listen to the Data Analyst and Compliance Analyst, then produce "
            "the final FinCEN BSA/AML Compliance Report. Structure:\n"
            "# MidwestBank — FinCEN BSA/AML Compliance Report Q4\n"
            "## Executive Summary\n"
            "## Transaction Monitoring Findings\n"
            "## SAR Filing Status\n"
            "## KYC/CDD Compliance\n"
            "## AML Pattern Analysis\n"
            "## Recommended Actions\n"
            "400-500 words. When the report is complete, end with 'TERMINATE'."
        ),
    )

    termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(max_messages=10)

    team = RoundRobinGroupChat(
        participants=[data_analyst, compliance_analyst, report_writer],
        termination_condition=termination,
    )

    task = (
        "Generate a complete FinCEN BSA/AML compliance report for MidwestBank Q4. "
        "Data Analyst: provide key data findings. "
        "Compliance Analyst: assess regulatory risks and obligations. "
        "Report Writer: synthesize into the final structured report."
    )

    result = await team.run(task=task)
    metrics.llm_calls = len(result.messages)

    # Extract final report from last non-user message
    final_text = ""
    for msg in reversed(result.messages):
        content = msg.content if hasattr(msg, "content") else str(msg)
        if content and "TERMINATE" not in content[:20] and hasattr(msg, "source") and msg.source != "user":
            final_text = content.replace("TERMINATE", "").strip()
            break

    return final_text


def run(metrics: RunMetrics) -> str:
    print(f"\n{'='*60}")
    print(f"  Now running the pipeline using {FRAMEWORK}")
    print(f"{'='*60}")

    report = asyncio.run(_run_async(metrics))
    print(f"\n[{FRAMEWORK}] Report generated ({len(report.split())} words)")
    print(f"\n{report[:800]}{'...' if len(report) > 800 else ''}")
    return report
