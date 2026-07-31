"""Pydantic AI runner — typed agents orchestrated inside a pydantic-graph state machine.

What makes this runner architecturally distinct from the other five: every stage
boundary is a *validated Pydantic model* rather than a free-text string, and the
pipeline shape (parallel fan-out, fan-in join, conditional retry loop) is declared
up front as a graph rather than emerging from conversation or task ordering.

  start → plan_sections ──map──> draft_section ──join──> review_sections → decision
                ^                                                            │
                └──────────────── "revise" (max 3 iterations) ───────────────┤
                                                                "approved" → synthesize → end
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_graph import (
    GraphBuilder,
    StepContext,
    TypeExpression,
    reduce_list_append,
)

from shared.metrics import RunMetrics
from shared.tools import (
    detect_aml_patterns,
    get_kyc_stats,
    get_risk_summary,
    get_sar_status,
    get_transaction_stats,
)

FRAMEWORK = "Pydantic AI"
MAX_REVIEW_ITERATIONS = 3

TASK_PROMPT = (
    "Generate a concise AML compliance section for MidwestBank's FinCEN report. "
    "Use the provided data summary to write a professional, factual compliance section "
    "covering the key findings. Be specific with numbers. 150-200 words."
)


# ── Typed contracts between stages ───────────────────────────────────────────
# The other five runners pass raw strings between stages. Here each boundary is a
# Pydantic model, so a malformed LLM response fails validation (and is retried by
# Pydantic AI) instead of silently flowing downstream as garbage text.

class SectionTopic(BaseModel):
    """One planned section of the compliance report."""

    id: str
    topic: str
    tool: str
    revision_notes: list[str] = Field(default_factory=list)


class SectionDraft(BaseModel):
    """A drafted report section."""

    section_id: str
    topic: str
    content: str
    key_figures: list[str] = Field(
        default_factory=list,
        description="Specific figures cited in the section, e.g. '1,204 suspicious transactions'.",
    )


class QualityReview(BaseModel):
    """Evaluator verdict on a batch of drafted sections."""

    approved: bool
    issues: list[str] = Field(default_factory=list)
    accuracy_score: int = Field(ge=1, le=5, description="1 = unusable, 5 = filing-ready.")


class FinalReport(BaseModel):
    """The assembled regulator-facing report."""

    executive_summary: str
    body: str


SECTION_TOPICS: list[SectionTopic] = [
    SectionTopic(id="aml_transactions", topic="AML Transaction Monitoring", tool="transaction_stats"),
    SectionTopic(id="sar_filings", topic="SAR Filing Status", tool="sar_status"),
    SectionTopic(id="kyc_cdd", topic="KYC/CDD Compliance", tool="kyc_stats"),
    SectionTopic(id="aml_patterns", topic="AML Pattern Detection", tool="aml_patterns"),
    SectionTopic(id="risk_summary", topic="Risk Indicators Summary", tool="risk_summary"),
]


# ── Dependency injection ─────────────────────────────────────────────────────

@dataclass
class ComplianceDeps:
    """Injected into every agent run and every tool via RunContext.

    Carrying RunMetrics here (rather than reaching for a module global) is the
    point of the pattern: tools record their own usage against the live run.
    """

    metrics: RunMetrics
    report_type: str = "FinCEN"


@dataclass
class ComplianceState:
    """Graph state, threaded through every node."""

    report_type: str = "FinCEN"
    iteration: int = 0
    issues: list[str] = field(default_factory=list)
    drafts: list[SectionDraft] = field(default_factory=list)
    accuracy_score: int = 0
    final_report: str = ""


def _model_name() -> str:
    return f"openai:{os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}"


def build_agents(model: object | None = None) -> tuple[Agent, Agent, Agent]:
    """Build the three typed agents.

    `model` is injectable so tests can pass pydantic_ai.models.test.TestModel and
    exercise the whole pipeline without touching the network.
    """
    m = model or _model_name()

    section_agent = Agent(
        m,
        deps_type=ComplianceDeps,
        output_type=SectionDraft,
        system_prompt=(
            "You are an AML compliance report writer for a mid-size U.S. bank. "
            "Call exactly one data tool to get the figures for your assigned section, "
            "then write it. Populate key_figures with the specific numbers you cited."
        ),
    )

    review_agent = Agent(
        m,
        deps_type=ComplianceDeps,
        output_type=QualityReview,
        system_prompt=(
            "You are a BSA/AML compliance reviewer. Evaluate drafted report sections for "
            "numerical accuracy, correct regulatory terminology (SAR, CTR, KYC, CDD, PEP), "
            "and internal consistency. Approve only if the sections are filing-ready."
        ),
    )

    synthesis_agent = Agent(
        m,
        deps_type=ComplianceDeps,
        output_type=FinalReport,
        system_prompt=(
            "You are a senior compliance officer assembling a regulatory filing. "
            "Write an executive summary, then the body combining the reviewed sections."
        ),
    )

    # Tools are shared business logic from shared/tools.py — identical to what the
    # other five runners call. Only the registration mechanism differs.
    _register_tools(section_agent)

    return section_agent, review_agent, synthesis_agent


def _register_tools(agent: Agent) -> None:
    """Wrap shared/tools.py functions as Pydantic AI tools with metrics tracking."""

    @agent.tool
    def transaction_stats(ctx: RunContext[ComplianceDeps]) -> str:
        """Transaction monitoring statistics: volumes, suspicious counts, CTR-eligible."""
        ctx.deps.metrics.tool_calls += 1
        return get_transaction_stats()

    @agent.tool
    def sar_status(ctx: RunContext[ComplianceDeps]) -> str:
        """Suspicious Activity Report filing status by status and type."""
        ctx.deps.metrics.tool_calls += 1
        return get_sar_status()

    @agent.tool
    def kyc_stats(ctx: RunContext[ComplianceDeps]) -> str:
        """KYC/CDD compliance statistics: verified, expired, pending, PEP, risk distribution."""
        ctx.deps.metrics.tool_calls += 1
        return get_kyc_stats()

    @agent.tool
    def aml_patterns(ctx: RunContext[ComplianceDeps]) -> str:
        """Detected AML red-flag patterns: structuring, layering, high-velocity."""
        ctx.deps.metrics.tool_calls += 1
        return detect_aml_patterns()

    @agent.tool
    def risk_summary(ctx: RunContext[ComplianceDeps]) -> str:
        """High-risk customer counts and priority remediation actions."""
        ctx.deps.metrics.tool_calls += 1
        return get_risk_summary()


def build_graph(agents: tuple[Agent, Agent, Agent] | None = None):
    """Assemble the compliance pipeline graph. Returns a built, runnable Graph."""
    section_agent, review_agent, synthesis_agent = agents or build_agents()

    g = GraphBuilder(
        name="compliance_pipeline",
        state_type=ComplianceState,
        deps_type=ComplianceDeps,
        output_type=str,
    )

    @g.step
    async def plan_sections(
        ctx: StepContext[ComplianceState, ComplianceDeps, None],
    ) -> list[SectionTopic]:
        """Plan the report sections, carrying any reviewer feedback into the retry."""
        ctx.state.drafts = []
        if not ctx.state.issues:
            return SECTION_TOPICS
        # On a retry, attach the reviewer's issues so drafters can correct them.
        return [t.model_copy(update={"revision_notes": ctx.state.issues}) for t in SECTION_TOPICS]

    @g.step
    async def draft_section(
        ctx: StepContext[ComplianceState, ComplianceDeps, SectionTopic],
    ) -> SectionDraft:
        """Draft one section. Runs in parallel across all five topics."""
        topic = ctx.inputs
        prompt = (
            f"Write the '{topic.topic}' section for the {ctx.state.report_type} report.\n"
            f"Call the `{topic.tool}` tool to get your data.\n\n{TASK_PROMPT}"
        )
        if topic.revision_notes:
            notes = "\n".join(f"- {n}" for n in topic.revision_notes)
            prompt += f"\n\nA reviewer rejected the previous draft. Fix these issues:\n{notes}"

        result = await section_agent.run(prompt, deps=ctx.deps)
        ctx.deps.metrics.llm_calls += 1
        # Trust the topic identity over whatever the model echoed back.
        return result.output.model_copy(update={"section_id": topic.id, "topic": topic.topic})

    collect_drafts = g.join(reduce_list_append, initial_factory=list[SectionDraft])

    @g.step
    async def review_sections(
        ctx: StepContext[ComplianceState, ComplianceDeps, list[SectionDraft]],
    ) -> Literal["approved", "revise"]:
        """Evaluate the batch. The retry decision is a validated bool, not parsed text."""
        ctx.state.drafts = ctx.inputs
        ctx.state.iteration += 1

        sections = "\n\n".join(f"## {d.topic}\n{d.content}" for d in ctx.inputs)
        result = await review_agent.run(
            f"Review these {ctx.state.report_type} report sections:\n\n{sections}",
            deps=ctx.deps,
        )
        ctx.deps.metrics.llm_calls += 1

        review = result.output
        ctx.state.accuracy_score = review.accuracy_score

        if review.approved:
            print(f"[{FRAMEWORK}] Review passed on iteration {ctx.state.iteration} "
                  f"(accuracy {review.accuracy_score}/5)")
            return "approved"

        if ctx.state.iteration >= MAX_REVIEW_ITERATIONS:
            print(f"[{FRAMEWORK}] Review cap reached after {MAX_REVIEW_ITERATIONS} "
                  f"iterations — proceeding with best effort")
            return "approved"

        print(f"[{FRAMEWORK}] Review iteration {ctx.state.iteration}: "
              f"{len(review.issues)} issue(s), redrafting")
        ctx.state.issues = review.issues
        return "revise"

    @g.step
    async def synthesize(
        ctx: StepContext[ComplianceState, ComplianceDeps, object],
    ) -> str:
        """Assemble the approved sections into the final regulator report."""
        sections = "\n\n".join(f"## {d.topic}\n{d.content}" for d in ctx.state.drafts)
        result = await synthesis_agent.run(
            f"Assemble the final {ctx.state.report_type} compliance report "
            f"from these reviewed sections:\n\n{sections}",
            deps=ctx.deps,
        )
        ctx.deps.metrics.llm_calls += 1

        out = result.output
        report = f"# Executive Summary\n\n{out.executive_summary}\n\n{out.body}"
        ctx.state.final_report = report
        return report

    g.add(
        g.edge_from(g.start_node).to(plan_sections),
        # .map() spreads the five topics into parallel drafting tasks — the
        # pydantic-graph analogue of LangGraph's Send fan-out.
        g.edge_from(plan_sections).map().to(draft_section),
        g.edge_from(draft_section).to(collect_drafts),
        g.edge_from(collect_drafts).to(review_sections),
        g.edge_from(review_sections).to(
            g.decision()
            .branch(g.match(TypeExpression[Literal["approved"]]).to(synthesize))
            .branch(g.match(TypeExpression[Literal["revise"]]).to(plan_sections))
        ),
        g.edge_from(synthesize).to(g.end_node),
    )

    return g.build()


def render_graph(direction: str = "TB") -> str:
    """Mermaid stateDiagram-v2 source for the pipeline (used in the README).

    Builds against TestModel so the diagram can be generated with no API key —
    the shape of the graph doesn't depend on which model runs inside it.
    """
    from pydantic_ai.models.test import TestModel

    return build_graph(build_agents(model=TestModel())).render(direction=direction)


async def _run_async(metrics: RunMetrics, agents=None) -> str:
    graph = build_graph(agents)
    state = ComplianceState(report_type="FinCEN")
    deps = ComplianceDeps(metrics=metrics, report_type="FinCEN")
    report = await graph.run(state=state, deps=deps)
    print(f"\n[{FRAMEWORK}] Completed in {state.iteration} review iteration(s), "
          f"{len(state.drafts)} sections")
    return report


def run(metrics: RunMetrics) -> str:
    """Entry point matching the contract used by every runner in this project."""
    print(f"\n{'='*60}")
    print(f"  Now running the pipeline using {FRAMEWORK}")
    print(f"{'='*60}")

    report = asyncio.run(_run_async(metrics))

    print(f"\n[{FRAMEWORK}] Report generated ({len(report.split())} words)")
    print(f"\n{report[:800]}{'...' if len(report) > 800 else ''}")
    return report
