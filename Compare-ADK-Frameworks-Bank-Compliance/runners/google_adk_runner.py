"""Google ADK runner — parallel fan-out + sequential synthesis + review loop."""
import asyncio
import os

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent, LoopAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.adk.tools import ToolContext
from google.genai import types

from shared.metrics import RunMetrics
from shared.tools import (
    detect_aml_patterns,
    get_kyc_stats,
    get_risk_summary,
    get_sar_status,
    get_transaction_stats,
)

FRAMEWORK = "Google ADK"


def _get_model():
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return LiteLlm(model=f"openai/{model_name}")


# Wrap shared tools as plain Python functions for Google ADK
def adk_get_transaction_stats() -> str:
    """Return AML transaction monitoring statistics for MidwestBank."""
    return get_transaction_stats()


def adk_get_sar_status() -> str:
    """Return SAR filing status and counts."""
    return get_sar_status()


def adk_get_kyc_stats() -> str:
    """Return KYC/CDD compliance statistics."""
    return get_kyc_stats()


def adk_detect_aml_patterns() -> str:
    """Detect AML red-flag patterns: structuring, layering, high-velocity."""
    return detect_aml_patterns()


def adk_get_risk_summary() -> str:
    """Return high-risk customer and priority risk indicators summary."""
    return get_risk_summary()


def exit_loop(tool_context: ToolContext) -> dict:
    """Signal that the report passes quality review — exit the loop."""
    tool_context.actions.escalate = True
    return {"status": "quality check passed — report approved"}


def build_pipeline():
    MODEL = _get_model()

    transaction_agent = LlmAgent(
        name="transaction_agent",
        model=MODEL,
        description="Analyses MidwestBank transactions for BSA/AML compliance",
        instruction=(
            "Use adk_get_transaction_stats and adk_detect_aml_patterns to retrieve data. "
            "Summarise: total transactions, suspicious count/percentage, CTR eligibility, "
            "and AML patterns detected. Cite exact numbers."
        ),
        tools=[adk_get_transaction_stats, adk_detect_aml_patterns],
        output_key="transaction_findings",
    )

    sar_kyc_agent = LlmAgent(
        name="sar_kyc_agent",
        model=MODEL,
        description="Reviews SAR filings and KYC compliance status",
        instruction=(
            "Use adk_get_sar_status and adk_get_kyc_stats to retrieve data. "
            "Summarise: total SARs by status and type, total amount involved, "
            "KYC verified/expired/pending counts, PEP customer count."
        ),
        tools=[adk_get_sar_status, adk_get_kyc_stats],
        output_key="sar_kyc_findings",
    )

    risk_agent = LlmAgent(
        name="risk_agent",
        model=MODEL,
        description="Assesses high-risk customers and priority actions",
        instruction=(
            "Use adk_get_risk_summary to retrieve data. "
            "Summarise high-risk customers, KYC deficiencies, pending SARs, "
            "and priority recommended actions."
        ),
        tools=[adk_get_risk_summary],
        output_key="risk_findings",
    )

    parallel_fetch = ParallelAgent(
        name="parallel_fetch",
        sub_agents=[transaction_agent, sar_kyc_agent, risk_agent],
        description="Fetch transaction, SAR/KYC, and risk data concurrently",
    )

    synthesize_agent = LlmAgent(
        name="synthesize_agent",
        model=MODEL,
        description="Synthesizes all findings into final compliance report",
        instruction=(
            "Produce the final MidwestBank FinCEN BSA/AML Compliance Report Q4 "
            "from the session state findings:\n"
            "  Transaction findings: {transaction_findings}\n"
            "  SAR/KYC findings: {sar_kyc_findings}\n"
            "  Risk findings: {risk_findings}\n\n"
            "Format:\n"
            "# MidwestBank — FinCEN BSA/AML Compliance Report Q4\n"
            "## Executive Summary\n"
            "## Transaction Monitoring\n"
            "## SAR Filing Status\n"
            "## KYC/CDD Compliance\n"
            "## Risk Indicators\n"
            "## Recommended Actions\n"
            "400-500 words. Cite specific numbers."
        ),
        output_key="final_report",
    )

    quality_critic = LlmAgent(
        name="quality_critic",
        model=MODEL,
        description="Reviews report quality — calls exit_loop if it passes",
        instruction=(
            "Review this compliance report: {final_report}\n\n"
            "Quality bar:\n"
            "1. Executive Summary mentions key risk metrics\n"
            "2. SAR section includes filing counts\n"
            "3. KYC section mentions expired/pending records\n"
            "4. Recommended Actions has at least 3 items\n\n"
            "If ALL pass: call exit_loop(). "
            "Otherwise briefly note which criteria failed."
        ),
        tools=[exit_loop],
        output_key="critic_feedback",
    )

    review_loop = LoopAgent(
        name="review_loop",
        sub_agents=[quality_critic],
        max_iterations=2,
        description="Quality check loop (max 2 iterations)",
    )

    pipeline = SequentialAgent(
        name="compliance_pipeline",
        sub_agents=[parallel_fetch, synthesize_agent, review_loop],
        description="Parallel fetch → synthesize → quality review",
    )

    return pipeline


async def _run_async(metrics: RunMetrics) -> str:
    pipeline = build_pipeline()
    runner = InMemoryRunner(agent=pipeline, app_name="midwest_compliance")

    session = await runner.session_service.create_session(
        app_name="midwest_compliance",
        user_id="compliance.officer",
        state={"bank_name": "MidwestBank", "quarter": "Q4"},
    )

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(
            text="Generate the Q4 FinCEN BSA/AML compliance report for MidwestBank. "
                 "Analyse all transaction data, SAR filings, KYC status, and risk indicators."
        )],
    )

    final_text = ""
    llm_calls = 0
    for event in runner.run(
        user_id="compliance.officer",
        session_id=session.id,
        new_message=content,
    ):
        if event.content and event.content.parts:
            text = event.content.parts[0].text or ""
            if text:
                llm_calls += 1
                final_text = text

    metrics.llm_calls = llm_calls
    metrics.tool_calls = 5
    return final_text


def run(metrics: RunMetrics) -> str:
    print(f"\n{'='*60}")
    print(f"  Now running the pipeline using {FRAMEWORK}")
    print(f"{'='*60}")

    report = asyncio.run(_run_async(metrics))
    print(f"\n[{FRAMEWORK}] Report generated ({len(report.split())} words)")
    print(f"\n{report[:800]}{'...' if len(report) > 800 else ''}")
    return report
