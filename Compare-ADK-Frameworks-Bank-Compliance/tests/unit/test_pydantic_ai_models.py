"""Tests for the typed stage contracts in runners/pydantic_ai_runner.py.

These models are the whole reason the Pydantic AI runner is architecturally distinct:
they are what turns a malformed LLM response into a validation error instead of a
plausible-looking wrong number in a regulatory filing.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from runners.pydantic_ai_runner import (
    MAX_REVIEW_ITERATIONS,
    SECTION_TOPICS,
    ComplianceState,
    FinalReport,
    QualityReview,
    SectionDraft,
)


class TestSectionDraft:
    def test_minimal_valid(self):
        d = SectionDraft(section_id="kyc_cdd", topic="KYC/CDD Compliance", content="text")
        assert d.key_figures == []

    def test_key_figures_default_is_not_shared(self):
        a = SectionDraft(section_id="a", topic="A", content="x")
        b = SectionDraft(section_id="b", topic="B", content="y")
        a.key_figures.append("1,204 suspicious transactions")
        assert b.key_figures == []

    def test_missing_required_field_rejected(self):
        with pytest.raises(ValidationError):
            SectionDraft(section_id="a", topic="A")

    def test_model_copy_update_overrides_identity(self):
        """The runner trusts its own topic identity over whatever the model echoed."""
        d = SectionDraft(section_id="hallucinated", topic="Wrong", content="text")
        fixed = d.model_copy(update={"section_id": "kyc_cdd", "topic": "KYC/CDD Compliance"})
        assert fixed.section_id == "kyc_cdd"
        assert fixed.topic == "KYC/CDD Compliance"
        assert fixed.content == "text"


class TestQualityReview:
    def test_valid(self):
        r = QualityReview(approved=True, accuracy_score=5)
        assert r.issues == []

    @pytest.mark.parametrize("score", [1, 2, 3, 4, 5])
    def test_accepts_in_range_scores(self, score):
        assert QualityReview(approved=False, accuracy_score=score).accuracy_score == score

    @pytest.mark.parametrize("score", [0, -1, 6, 99])
    def test_rejects_out_of_range_scores(self, score):
        with pytest.raises(ValidationError):
            QualityReview(approved=False, accuracy_score=score)

    def test_approved_must_be_present(self):
        with pytest.raises(ValidationError):
            QualityReview(accuracy_score=3)

    def test_approved_is_a_real_bool_not_a_string(self):
        """The retry decision branches on this field — it must not be a loose string."""
        r = QualityReview(approved=False, accuracy_score=2, issues=["bad total"])
        assert r.approved is False
        assert isinstance(r.approved, bool)


class TestFinalReport:
    def test_valid(self):
        r = FinalReport(executive_summary="summary", body="body")
        assert r.executive_summary == "summary"

    def test_both_fields_required(self):
        with pytest.raises(ValidationError):
            FinalReport(executive_summary="only summary")


class TestSectionTopics:
    def test_five_topics(self):
        assert len(SECTION_TOPICS) == 5

    def test_ids_are_unique(self):
        ids = [t.id for t in SECTION_TOPICS]
        assert len(ids) == len(set(ids))

    def test_topics_match_the_pipeline_in_the_readme(self):
        assert {t.id for t in SECTION_TOPICS} == {
            "aml_transactions", "sar_filings", "kyc_cdd", "aml_patterns", "risk_summary",
        }

    def test_every_topic_maps_to_a_registered_tool(self):
        """A topic pointing at a tool the agent doesn't have would silently degrade
        that section to an unsourced guess."""
        from runners import pydantic_ai_runner as r

        available = {
            "transaction_stats", "sar_status", "kyc_stats", "aml_patterns", "risk_summary",
        }
        for topic in r.SECTION_TOPICS:
            assert topic.tool in available, f"{topic.id} references unknown tool {topic.tool}"

    def test_revision_notes_default_empty(self):
        assert all(t.revision_notes == [] for t in SECTION_TOPICS)

    def test_revision_notes_attach_via_copy(self):
        t = SECTION_TOPICS[0].model_copy(update={"revision_notes": ["fix the CTR total"]})
        assert t.revision_notes == ["fix the CTR total"]
        assert SECTION_TOPICS[0].revision_notes == [], "the shared topic list was mutated"


class TestComplianceState:
    def test_defaults(self):
        s = ComplianceState()
        assert s.report_type == "FinCEN"
        assert s.iteration == 0
        assert s.drafts == []
        assert s.issues == []
        assert s.final_report == ""

    def test_mutable_defaults_are_per_instance(self):
        a, b = ComplianceState(), ComplianceState()
        a.drafts.append(SectionDraft(section_id="x", topic="X", content="c"))
        a.issues.append("issue")
        assert b.drafts == []
        assert b.issues == []


def test_max_review_iterations_matches_the_readme():
    """The README promises 'iterates up to 3 times per section until quality passes'."""
    assert MAX_REVIEW_ITERATIONS == 3
