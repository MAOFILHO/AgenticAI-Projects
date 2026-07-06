"""CLI harness: drives synthetic tickets through the full agent system and
produces a side-by-side comparison of all 10 inter-service communication
protocols (REST, GraphQL, gRPC, Webhook, WebSocket, MQTT, AMQP, SOAP, MCP,
A2A) — measured live, inside each specialist agent's real tool-calling loop.

Usage:
    make benchmark
    python apps/benchmark_runner.py [num_tickets]

Prerequisites:
    make protocols-up   # REST, GraphQL, gRPC, Webhook, WebSocket, SOAP
    make brokers-up     # Mosquitto + RabbitMQ (Docker), for MQTT/AMQP
    make responders-up  # MQTT + AMQP responder subprocesses
"""

import socket
import sys
import time

from shopsmart.charts import plot_protocol_comparison
from shopsmart.config import get_mqtt_broker_host, get_mqtt_broker_port, get_output_dir
from shopsmart.data_loader import select_benchmark_tickets
from shopsmart.graph import build_system, process_ticket

ALL_PROTOCOLS = ["REST", "GRAPHQL", "GRPC", "WEBHOOK", "WS", "MQTT", "AMQP", "SOAP", "MCP", "A2A"]

_PREREQ_PORTS = {
    "REST (8001)": ("127.0.0.1", 8001),
    "GraphQL (8002)": ("127.0.0.1", 8002),
    "gRPC (8003)": ("127.0.0.1", 8003),
    "Webhook (8004)": ("127.0.0.1", 8004),
    "WebSocket (8005)": ("127.0.0.1", 8005),
    "SOAP (8006)": ("127.0.0.1", 8006),
}


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _check_prerequisites():
    print("[Benchmark] Step 1/4 -- Checking protocol server availability...")
    all_ok = True
    for label, (host, port) in _PREREQ_PORTS.items():
        ok = _port_open(host, port)
        print(f"    {'OK ' if ok else 'MISSING'} {label}")
        all_ok = all_ok and ok

    mqtt_ok = _port_open(get_mqtt_broker_host(), get_mqtt_broker_port())
    print(f"    {'OK ' if mqtt_ok else 'MISSING'} MQTT broker (Mosquitto, {get_mqtt_broker_port()})")
    amqp_ok = _port_open("127.0.0.1", 5672)
    print(f"    {'OK ' if amqp_ok else 'MISSING'} AMQP broker (RabbitMQ, 5672)")

    if not all_ok:
        print("    -> Run `make protocols-up` in another terminal to start missing servers.")
    if not (mqtt_ok and amqp_ok):
        print("    -> Run `make brokers-up && make responders-up` for MQTT/AMQP.")
    print()


def main():
    num_tickets = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    print("=" * 70)
    print("ShopSmart Communication Protocol Benchmark")
    print("=" * 70)
    print()

    _check_prerequisites()

    print(
        "[Benchmark] Step 2/4 -- Building the multi-agent system "
        "(LLMs, RAG index, MCP tools, A2A registry)..."
    )
    start = time.time()
    graph, memory, store, data, known_names, langfuse_handler, metrics = build_system()
    print(f"    Done in {time.time() - start:.1f}s.\n")

    tickets = select_benchmark_tickets(data["tickets"], num_tickets)
    print(
        f"[Benchmark] Step 3/4 -- Processing {len(tickets)} tickets (category-balanced "
        f"selection) through the live agent tool-calling loop..."
    )
    for i, ticket in enumerate(tickets, start=1):
        print(f"    [{i}/{len(tickets)}] {ticket['ticket_id']} ({ticket.get('category', '?')})...", end=" ", flush=True)
        t0 = time.time()
        try:
            process_ticket(ticket, graph, data, known_names, langfuse_handler=langfuse_handler)
            print(f"ok ({time.time() - t0:.1f}s)")
        except Exception as exc:
            print(f"FAILED: {exc}")
    print()

    print("[Benchmark] Step 4/4 -- Protocol comparison results\n")
    metrics.print_summary()

    stats = metrics.protocol_stats
    missing = [p for p in ALL_PROTOCOLS if p not in stats]
    if missing:
        print(f"Note: not exercised in this run (0 calls): {', '.join(missing)}")
        print("      Try increasing num_tickets, or check that ticket categories map to the")
        print("      specialists that own these tools.\n")

    report_path = get_output_dir() / "protocol_benchmark_report.json"
    with open(report_path, "w") as f:
        f.write(metrics.export_json())
    print(f"[Benchmark] Full metrics JSON written to {report_path}")

    if stats:
        plot_protocol_comparison(stats)
    else:
        print("[Benchmark] No protocol calls recorded -- skipping chart.")


if __name__ == "__main__":
    main()
