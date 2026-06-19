"""OpenAI Agents SDK runner — handoff-based orchestration with specialist agents."""
import asyncio
import os

from agents import Agent, Runner, function_tool
from shared.metrics import RunMetrics
from shared.tools import (
    get_transaction_stats,
    get_sar_status,
    get_kyc_stats,
    detect_aml_patterns,
    get_risk_summary,
)

FRAMEWORK = "OpenAI Agent SDK"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


@function_tool
def tool_get_transaction_stats() -> str:
    """Get AML transaction monitoring statistics for MidwestBank."""
    return get_transaction_stats()


@function_tool
def tool_get_sar_status() -> str:
    """Get SAR (Suspicious Activity Report) filing status."""
    return get_sar_status()


@function_tool
def tool_get_kyc_stats() -> str:
    """Get KYC/CDD compliance statistics."""
    return get_kyc_stats()


@function_tool
def tool_detect_aml_patterns() -> str:
    """Detect AML red-flag patterns: structuring, layering, high-velocity."""
    return detect_aml_patterns()


@function_tool
def tool_get_risk_summary() -> str:
    """Get high-risk customer and priority risk indicators summary."""
    return get_risk_summary()


def build_agents():
    aml_agent = Agent(
        name="AML_Transaction_Analyst",
        model=MODEL,
        instructions=(
            "You are a BSA/AML compliance analyst for MidwestBank. "
            "Use your tools to retrieve transaction data and SAR filings, "
            "then write a concise compliance analysis section (150-200 words). "
            "Be specific with numbers. Cite dollar amounts and percentages."
        ),
        tools=[tool_get_transaction_stats, tool_get_sar_status, tool_detect_aml_patterns],
    )

    kyc_agent = Agent(
        name="KYC_Compliance_Specialist",
        model=MODEL,
        instructions=(
            "You are a KYC/CDD compliance specialist for MidwestBank. "
            "Use your tools to retrieve KYC statistics and risk summaries, "
            "then write a concise compliance section (150-200 words). "
            "Highlight expired KYC, PEP customers, and high-risk accounts."
        ),
        tools=[tool_get_kyc_stats, tool_get_risk_summary],
    )

    report_writer = Agent(
        name="Compliance_Report_Writer",
        model=MODEL,
        instructions=(
            "You are a senior compliance report writer for MidwestBank. "
            "You receive analysis from the AML analyst and KYC specialist. "
            "Synthesize their findings into a final FinCEN compliance report "
            "with an Executive Summary and key findings. 400-500 words total. "
            "Structure: Executive Summary, AML/Transaction Monitoring, KYC/CDD, "
            "Recommended Actions."
        ),
        handoffs=[aml_agent, kyc_agent],
    )

    triage_agent = Agent(
        name="Compliance_Triage",
        model=MODEL,
        instructions=(
            "You are the compliance triage agent for MidwestBank. "
            "Route incoming compliance requests to the right specialist: "
            "- AML/transaction queries → AML_Transaction_Analyst "
            "- KYC/customer risk queries → KYC_Compliance_Specialist "
            "- Report synthesis requests → Compliance_Report_Writer "
            "For a full compliance report request, start with AML then KYC then report."
        ),
        handoffs=[aml_agent, kyc_agent, report_writer],
    )

    return triage_agent


async def _run_async(metrics: RunMetrics) -> str:
    triage = build_agents()
    result = await Runner.run(
        triage,
        "Generate a complete FinCEN BSA/AML compliance report for MidwestBank Q4. "
        "First analyze transactions and SARs, then review KYC compliance, "
        "then synthesize a final report with executive summary and recommended actions.",
    )
    metrics.llm_calls = 4
    metrics.tool_calls = 5
    return result.final_output


def run(metrics: RunMetrics) -> str:
    print(f"\n{'='*60}")
    print(f"  Now running the pipeline using {FRAMEWORK}")
    print(f"{'='*60}")

    report = asyncio.run(_run_async(metrics))
    print(f"\n[{FRAMEWORK}] Report generated ({len(report.split())} words)")
    print(f"\n{report[:800]}{'...' if len(report) > 800 else ''}")
    return report
