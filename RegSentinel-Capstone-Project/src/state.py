"""Shared LangGraph state for the RegSentinel compliance pipeline."""
import operator
from typing import Annotated, TypedDict


class ComplianceState(TypedDict, total=False):
    user_request: str

    # Parallel fan-out: each worker appends; operator.add reducer concatenates
    findings: Annotated[list, operator.add]
    guardrail_alerts: Annotated[list, operator.add]

    # Single-writer keys
    regulation_findings: str
    transaction_findings: str
    audit_findings: str
    classified_findings: str
    scored_findings: str
    final_report: str
    critic_feedback: str
    quality_passed: bool
    revision_count: int
