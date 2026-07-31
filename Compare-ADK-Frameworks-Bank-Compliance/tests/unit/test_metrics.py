"""Tests for shared/metrics.py — the comparison table is only as honest as this."""
from __future__ import annotations

import time

from shared.metrics import RunMetrics


def test_defaults():
    m = RunMetrics(framework="LangGraph")
    assert m.framework == "LangGraph"
    assert m.status == "pending"
    assert m.llm_calls == 0
    assert m.tool_calls == 0
    assert m.report_word_count == 0
    assert m.error is None
    assert m.end_time is None


def test_finish_sets_success_and_word_count():
    m = RunMetrics(framework="X")
    m.finish("one two three four five")
    assert m.status == "success"
    assert m.report_word_count == 5
    assert m.end_time is not None
    assert m.error is None


def test_finish_with_empty_output_leaves_counts_zero():
    m = RunMetrics(framework="X")
    m.finish("")
    assert m.status == "success"
    assert m.report_word_count == 0
    assert m.output_preview == ""


def test_output_preview_is_truncated():
    m = RunMetrics(framework="X")
    m.finish("word " * 500)
    assert len(m.output_preview) == 500


def test_fail_sets_error_and_status():
    m = RunMetrics(framework="X")
    m.fail("boom")
    assert m.status == "error"
    assert m.error == "boom"
    assert m.end_time is not None
    assert m.report_word_count == 0


def test_elapsed_seconds_is_frozen_after_finish():
    m = RunMetrics(framework="X")
    m.finish("done")
    first = m.elapsed_seconds
    time.sleep(0.01)
    assert m.elapsed_seconds == first


def test_elapsed_seconds_ticks_while_pending():
    m = RunMetrics(framework="X", start_time=time.time() - 5)
    assert m.elapsed_seconds >= 5


def test_counters_are_independent_between_instances():
    a = RunMetrics(framework="A")
    b = RunMetrics(framework="B")
    a.llm_calls += 3
    a.tool_calls += 2
    assert b.llm_calls == 0
    assert b.tool_calls == 0
