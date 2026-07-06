"""System metrics tracking, summary, and export."""

import json
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class ProtocolCallResult:
    """One recorded attempt of a protocol call (REST, GraphQL, gRPC, ...)."""

    protocol: str
    latency_ms: float
    payload_bytes: int
    success: bool
    error_type: str | None
    retry_count: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class SystemMetrics:
    """Tracks operational metrics for the ShopSmart support system."""

    total_tickets: int = 0
    category_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    priority_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    tool_usage: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    latencies: list[float] = field(default_factory=list)
    routing_results: list[dict] = field(default_factory=list)
    escalation_count: int = 0
    quick_answer_count: int = 0
    correct_routes: int = 0
    total_routes: int = 0
    protocol_results: list[ProtocolCallResult] = field(default_factory=list)

    def record_protocol_call(self, result: ProtocolCallResult):
        self.protocol_results.append(result)

    @property
    def protocol_stats(self) -> dict:
        """Per-protocol p50/p95 latency, avg payload size, error/retry rate, call count."""
        by_protocol: dict[str, list[ProtocolCallResult]] = defaultdict(list)
        for r in self.protocol_results:
            by_protocol[r.protocol].append(r)

        stats = {}
        for protocol, results in by_protocol.items():
            latencies = [r.latency_ms for r in results]
            payloads = [r.payload_bytes for r in results]
            errors = [r for r in results if not r.success]
            retries = [r for r in results if r.retry_count > 0]

            p50 = statistics.median(latencies) if latencies else 0.0
            p95 = (
                statistics.quantiles(latencies, n=100)[94]
                if len(latencies) >= 2
                else (latencies[0] if latencies else 0.0)
            )

            stats[protocol] = {
                "call_count": len(results),
                "p50_latency_ms": round(p50, 2),
                "p95_latency_ms": round(p95, 2),
                "avg_payload_bytes": round(sum(payloads) / len(payloads), 1) if payloads else 0.0,
                "error_rate": round(len(errors) / len(results) * 100, 1) if results else 0.0,
                "retry_rate": round(len(retries) / len(results) * 100, 1) if results else 0.0,
            }
        return stats

    def record_ticket(self, result: dict, latency: float = 0.0):
        self.total_tickets += 1
        self.category_counts[result.get("category", "unknown")] += 1
        self.priority_counts[result.get("priority", "unknown")] += 1
        self.latencies.append(latency)

        for tool in result.get("tools_used", []):
            self.tool_usage[tool] += 1

        if result.get("needs_escalation"):
            self.escalation_count += 1
        if "quick_answer_lookup" in result.get("tools_used", []):
            self.quick_answer_count += 1

    def record_routing(self, expected: str, actual: str, confidence: float):
        self.total_routes += 1
        correct = expected == actual
        if correct:
            self.correct_routes += 1
        self.routing_results.append({
            "expected": expected,
            "actual": actual,
            "confidence": confidence,
            "correct": correct,
        })

    @property
    def routing_accuracy(self) -> float:
        return (self.correct_routes / self.total_routes * 100) if self.total_routes else 0.0

    @property
    def avg_latency(self) -> float:
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0.0

    @property
    def escalation_rate(self) -> float:
        return (self.escalation_count / self.total_tickets * 100) if self.total_tickets else 0.0

    @property
    def quick_answer_rate(self) -> float:
        return (self.quick_answer_count / self.total_tickets * 100) if self.total_tickets else 0.0

    def print_summary(self):
        print("=" * 70)
        print("SYSTEM SUMMARY: ShopSmart Customer Support Multi-Agent System")
        print("=" * 70)
        print()
        print("Architecture:")
        print("  Graph Nodes:          8 (supervisor + 5 handlers + escalation + formatter)")
        print("  Specialist Agents:    4 (order, returns, billing, product)")
        print("  Tools:                20 (MCP-enabled, 10 protocols benchmarked)")
        print("  Primary LLM:          gpt-5-mini")
        print("  Secondary LLM:        gpt-4.1-mini (temperature=0.3)")
        print("  RAG:                  FAISS + text-embedding-3-small")
        print()
        print("Patterns:")
        print("  [x] Supervisor Router (structured output classification)")
        print("  [x] Specialist Sub-Agents (tool-calling agents)")
        print("  [x] Deterministic Quick-Answer (no LLM for simple lookups)")
        print("  [x] RAG Policy Lookup (FAISS + semantic search)")
        print("  [x] PII Redaction (regex + database-driven)")
        print("  [x] HITL Escalation (interrupt + Command resume)")
        print("  [x] Thread Memory (MemorySaver)")
        print("  [x] Cross-Session Store (InMemoryStore)")
        print("  [x] MCP Protocol (FastMCP)")
        print("  [x] A2A Protocol (Google A2A spec)")
        print("  [x] Protocol Benchmark (REST/GraphQL/gRPC/Webhook/WebSocket/MQTT/AMQP/SOAP/MCP/A2A)")
        print("  [x] Observability (LangSmith + Langfuse)")
        print()

        if self.total_tickets > 0:
            print("Operational Metrics:")
            print(f"  Tickets Processed:    {self.total_tickets}")
            print(f"  Avg Latency:          {self.avg_latency:.2f}s")
            print(f"  Escalation Rate:      {self.escalation_rate:.1f}%")
            print(f"  Quick Answer Rate:    {self.quick_answer_rate:.1f}%")
            print()

            if self.total_routes > 0:
                print(f"  Routing Accuracy:     {self.routing_accuracy:.1f}% ({self.correct_routes}/{self.total_routes})")
                print()

            print("  Category Distribution:")
            for cat, count in sorted(self.category_counts.items()):
                pct = count / self.total_tickets * 100
                print(f"    {cat:<20} {count:>4} ({pct:.0f}%)")
            print()

            print("  Tool Usage:")
            for tool, count in sorted(self.tool_usage.items(), key=lambda x: -x[1]):
                print(f"    {tool:<30} {count:>4}")
            print()

        if self.protocol_results:
            print("Protocol Benchmark:")
            print(f"  {'Protocol':<12} {'Calls':>6} {'p50 ms':>9} {'p95 ms':>9} {'Payload B':>10} {'Err %':>7} {'Retry %':>8}")
            for protocol, s in sorted(self.protocol_stats.items()):
                print(
                    f"  {protocol:<12} {s['call_count']:>6} {s['p50_latency_ms']:>9} "
                    f"{s['p95_latency_ms']:>9} {s['avg_payload_bytes']:>10} "
                    f"{s['error_rate']:>7} {s['retry_rate']:>8}"
                )
            print()

        print("=" * 70)

    def export_json(self) -> str:
        return json.dumps({
            "total_tickets": self.total_tickets,
            "avg_latency": round(self.avg_latency, 3),
            "routing_accuracy": round(self.routing_accuracy, 1),
            "escalation_rate": round(self.escalation_rate, 1),
            "quick_answer_rate": round(self.quick_answer_rate, 1),
            "category_counts": dict(self.category_counts),
            "priority_counts": dict(self.priority_counts),
            "tool_usage": dict(self.tool_usage),
            "protocol_stats": self.protocol_stats,
        }, indent=2)


if __name__ == "__main__":
    metrics = SystemMetrics()
    metrics.print_summary()
