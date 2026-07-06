# ShopSmart Support — System Metrics Reference

## Operational Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **Routing Accuracy** | % of tickets correctly classified by supervisor | ≥ 80% |
| **Avg Latency** | Mean time from ticket submission to final response | < 5s |
| **Escalation Rate** | % of tickets requiring HITL human review | < 15% |
| **Quick Answer Rate** | % of tickets resolved via deterministic path (no LLM) | 30-40% |
| **Tool Usage** | Frequency of each tool invocation across tickets | — |
| **Category Distribution** | Breakdown of tickets by category | — |
| **Priority Distribution** | Breakdown of tickets by priority level | — |

## Observability Metrics (LangSmith + Langfuse)

| Metric | Platform | Description |
|--------|----------|-------------|
| **Trace Latency** | Both | Per-node execution time breakdown |
| **Token Usage** | Both | Input/output tokens per LLM call |
| **Cost per Ticket** | Both | $ cost per ticket (auto-computed from tokens) |
| **Custom Scores** | Both | Routing accuracy score per classification |
| **Error Rate** | Both | Failed LLM calls or tool errors |

## Benchmark Baselines

Based on initial testing with 20-ticket batch:

| Metric | Baseline |
|--------|----------|
| Routing Accuracy | ~85-95% |
| Avg Latency (quick_answer) | < 0.5s |
| Avg Latency (specialist) | 2-4s |
| Avg Latency (HITL) | Depends on human response time |
| Escalation Rate | ~10-15% (with platinum customer in dataset) |
| Quick Answer Rate | ~35% (order_status with order ID) |

## CLI Commands

```bash
make metrics    # Print system summary to stdout
make test       # Run full test suite (includes routing accuracy)
make smoke      # Quick validation (no API key required for offline tests)
```
