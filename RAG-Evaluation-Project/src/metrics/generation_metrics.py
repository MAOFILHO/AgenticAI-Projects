"""End-to-end (generation) metrics via LLM-as-judge.

- Answer Relevance (1-5): does the answer address the question?
- Groundedness (1-5): is every claim supported by the retrieved context?
- Hallucination Rate (0.0-1.0): fraction of claims not supported by context.
- Coherence (1-5): logical flow, structure, readability.
"""
import json

import numpy as np


def _llm_judge(prompt, llm):
    """Send a judging prompt to the LLM and parse its JSON response."""
    result = llm.invoke(prompt)
    text = result.content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, IndexError):
        return None


def evaluate_answer_relevance(question, answer, llm):
    prompt = f"""Rate how well the answer addresses the question (1-5).
1=Completely irrelevant  2=Partially relevant  3=Moderate  4=Highly relevant  5=Perfect

Question: {question}
Answer: {answer}

Return ONLY JSON: {{"score": <int>, "reason": "<brief>"}}"""
    return _llm_judge(prompt, llm)


def evaluate_groundedness(context, answer, llm):
    prompt = f"""Check if every claim in the answer is supported by the context (1-5).
1=Unsupported  2=Poorly supported  3=Partially  4=Well supported  5=Fully supported

Context: {context[:3000]}
Answer: {answer}

Return ONLY JSON: {{"score": <int>, "reason": "<brief>"}}"""
    return _llm_judge(prompt, llm)


def evaluate_hallucination_rate(context, answer, llm):
    prompt = f"""Count factual claims in the answer. Check each against context.

Context: {context[:3000]}
Answer: {answer}

Return ONLY JSON: {{"total_claims": <int>, "unsupported_claims": <int>, "hallucination_rate": <float 0.0-1.0>, "reason": "<brief>"}}"""
    return _llm_judge(prompt, llm)


def evaluate_coherence(answer, llm):
    prompt = f"""Rate the coherence of the answer: logical flow, structure, and readability (1-5).
1=Incoherent  2=Hard to follow  3=Adequate  4=Clear  5=Excellent

Answer: {answer}

Return ONLY JSON: {{"score": <int>, "reason": "<brief>"}}"""
    return _llm_judge(prompt, llm)


def evaluate_answer(question, context, answer, judge_llm):
    """Run all four LLM-as-judge metrics for a single (question, context, answer) triple."""
    rel = evaluate_answer_relevance(question, answer, judge_llm)
    grd = evaluate_groundedness(context, answer, judge_llm)
    hal = evaluate_hallucination_rate(context, answer, judge_llm)
    coh = evaluate_coherence(answer, judge_llm)

    return {
        "answer_relevance": rel.get("score", 0) if rel else 0,
        "groundedness": grd.get("score", 0) if grd else 0,
        "hallucination_rate": hal.get("hallucination_rate", -1) if hal else -1,
        "coherence": coh.get("score", 0) if coh else 0,
    }


def aggregate_generation_metrics(per_query_results):
    """Average per-query LLM-as-judge scores into summary generation metrics."""
    rel_scores = [r["answer_relevance"] for r in per_query_results if r["answer_relevance"] > 0]
    grd_scores = [r["groundedness"] for r in per_query_results if r["groundedness"] > 0]
    hal_rates = [r["hallucination_rate"] for r in per_query_results if r["hallucination_rate"] >= 0]
    coh_scores = [r["coherence"] for r in per_query_results if r["coherence"] > 0]

    return {
        "Answer Relevance (1-5)": float(np.mean(rel_scores)) if rel_scores else 0.0,
        "Groundedness (1-5)": float(np.mean(grd_scores)) if grd_scores else 0.0,
        "Hallucination Rate (0-1)": float(np.mean(hal_rates)) if hal_rates else 0.0,
        "Coherence (1-5)": float(np.mean(coh_scores)) if coh_scores else 0.0,
    }
