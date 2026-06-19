"""CrewAI runner — role-based sequential multi-agent orchestration."""
import os

from crewai import Agent, Crew, Process, Task
from crewai.tools import tool

from shared.metrics import RunMetrics
from shared.tools import (
    detect_aml_patterns,
    get_kyc_stats,
    get_risk_summary,
    get_sar_status,
    get_transaction_stats,
)

FRAMEWORK = "CrewAI"
MODEL = f"openai/{os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}"


@tool("Get Transaction Statistics")
def crew_get_transaction_stats(query: str = "") -> str:
    """Get AML transaction monitoring statistics including suspicious transactions and CTR eligibility."""
    return get_transaction_stats()


@tool("Get SAR Status")
def crew_get_sar_status(query: str = "") -> str:
    """Get SAR (Suspicious Activity Report) filing status and counts by type."""
    return get_sar_status()


@tool("Get KYC Statistics")
def crew_get_kyc_stats(query: str = "") -> str:
    """Get KYC/CDD compliance statistics including expired and pending verifications."""
    return get_kyc_stats()


@tool("Detect AML Patterns")
def crew_detect_aml_patterns(query: str = "") -> str:
    """Detect AML red-flag patterns such as structuring, layering, high-velocity transactions."""
    return detect_aml_patterns()


@tool("Get Risk Summary")
def crew_get_risk_summary(query: str = "") -> str:
    """Get high-risk customer summary and priority compliance actions."""
    return get_risk_summary()


def run(metrics: RunMetrics) -> str:
    print(f"\n{'='*60}")
    print(f"  Now running the pipeline using {FRAMEWORK}")
    print(f"{'='*60}")

    researcher = Agent(
        role="BSA/AML Research Analyst",
        goal="Gather all relevant transaction, SAR, and KYC data for the compliance report",
        backstory=(
            "You are MidwestBank's senior BSA research analyst with 10 years tracking "
            "transaction monitoring, SAR filings, and KYC compliance. You always cite "
            "exact numbers from the data tools."
        ),
        tools=[crew_get_transaction_stats, crew_get_sar_status, crew_get_kyc_stats,
               crew_detect_aml_patterns, crew_get_risk_summary],
        llm=MODEL,
        verbose=False,
    )

    aml_analyst = Agent(
        role="AML Compliance Analyst",
        goal="Analyze BSA/AML data and identify key compliance risks and required filings",
        backstory=(
            "You are MidwestBank's AML compliance analyst. You review transaction data "
            "for suspicious patterns, evaluate SAR filing obligations, and assess KYC "
            "deficiencies. You are precise with regulatory thresholds."
        ),
        llm=MODEL,
        verbose=False,
    )

    compliance_writer = Agent(
        role="Regulatory Compliance Report Writer",
        goal="Produce a structured FinCEN compliance report from the research and analysis",
        backstory=(
            "You are MidwestBank's compliance report writer. You produce clear, "
            "structured FinCEN reports with Executive Summary, findings by category, "
            "and recommended actions. You write for regulators — precise and professional."
        ),
        llm=MODEL,
        verbose=False,
    )

    research_task = Task(
        description=(
            "Use all available tools to gather MidwestBank's compliance data: "
            "transaction statistics, SAR filing status, KYC compliance metrics, "
            "AML pattern detection results, and risk summary. Produce a data brief "
            "with all key numbers."
        ),
        agent=researcher,
        expected_output="A data brief with transaction stats, SAR counts, KYC metrics, AML patterns, and risk indicators.",
    )

    analysis_task = Task(
        description=(
            "Analyze the research brief. Identify: (1) suspicious transaction patterns "
            "requiring SAR filing, (2) KYC deficiencies needing remediation, "
            "(3) high-risk customers requiring enhanced due diligence, "
            "(4) priority compliance actions. Write a structured analysis (200-250 words)."
        ),
        agent=aml_analyst,
        expected_output="Compliance analysis with identified risks, SAR obligations, KYC gaps, and priority actions.",
    )

    report_task = Task(
        description=(
            "Write the final FinCEN BSA/AML Compliance Report for MidwestBank Q4. "
            "Structure: Executive Summary, Transaction Monitoring Findings, "
            "SAR Filing Status, KYC/CDD Compliance, AML Pattern Analysis, "
            "Recommended Actions. 400-500 words total. Professional regulatory tone."
        ),
        agent=compliance_writer,
        expected_output="A complete, structured FinCEN compliance report ready for regulatory submission.",
    )

    crew = Crew(
        agents=[researcher, aml_analyst, compliance_writer],
        tasks=[research_task, analysis_task, report_task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()
    metrics.llm_calls = 3
    metrics.tool_calls = 5

    report = str(result)
    print(f"\n[{FRAMEWORK}] Report generated ({len(report.split())} words)")
    print(f"\n{report[:800]}{'...' if len(report) > 800 else ''}")
    return report
