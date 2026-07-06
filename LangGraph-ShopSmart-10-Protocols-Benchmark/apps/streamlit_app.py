"""ShopSmart Customer Support — Streamlit Web Application."""

import json
import time
import uuid

import streamlit as st
from langchain_core.messages import HumanMessage
from langgraph.types import Command


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="ShopSmart Support",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — ShopSmart branding
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #0078D4, #00BCF2);
        padding: 1.5rem 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .main-header h1 { color: white; margin: 0; font-size: 2rem; }
    .main-header p { color: #E0E0E0; margin: 0.25rem 0 0 0; }
    .metric-card {
        background: #f8f9fa;
        border-left: 4px solid #0078D4;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.5rem;
    }
    .escalation-card {
        background: #FFF3E0;
        border-left: 4px solid #FF9800;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 1rem;
    }
    .stChatMessage { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
def init_session():
    if "system" not in st.session_state:
        st.session_state.system = None
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = f"thread-{uuid.uuid4().hex[:8]}"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "metrics_data" not in st.session_state:
        st.session_state.metrics_data = {
            "total": 0,
            "categories": {},
            "latencies": [],
            "escalations": 0,
            "quick_answers": 0,
        }
    if "escalation_queue" not in st.session_state:
        st.session_state.escalation_queue = []
    if "system_ready" not in st.session_state:
        st.session_state.system_ready = False


init_session()


# ---------------------------------------------------------------------------
# System loader
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading ShopSmart Support System...")
def load_system():
    from shopsmart.config import load_env
    load_env()
    from shopsmart.graph import build_system
    return build_system()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shopping-cart.png", width=64)
    st.markdown("### ShopSmart Support")
    st.markdown("---")

    if st.button("🔄 Initialize System", width="stretch"):
        try:
            system = load_system()
            st.session_state.system = system
            st.session_state.system_ready = True
            st.success("System ready!")
        except Exception as e:
            st.error(f"Failed to initialize: {e}")

    st.markdown("---")

    if st.session_state.system_ready:
        st.markdown("**System Status:** 🟢 Online")
    else:
        st.markdown("**System Status:** 🔴 Not initialized")
        st.caption("Click 'Initialize System' to start")

    st.markdown("---")
    st.markdown("**Models:**")
    st.caption("Primary: gpt-5-mini")
    st.caption("Secondary: gpt-4.1-mini")

    st.markdown("---")
    st.markdown(f"**Thread:** `{st.session_state.thread_id[:16]}...`")
    if st.button("🔄 New Conversation", width="stretch"):
        st.session_state.thread_id = f"thread-{uuid.uuid4().hex[:8]}"
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown("**Observability:**")
    import os
    ls_active = bool(os.getenv("LANGSMITH_API_KEY"))
    lf_active = bool(os.getenv("LANGFUSE_PUBLIC_KEY"))
    st.caption(f"LangSmith: {'🟢' if ls_active else '🔴'}")
    st.caption(f"Langfuse: {'🟢' if lf_active else '🔴'}")


# ---------------------------------------------------------------------------
# Main content — Tabs
# ---------------------------------------------------------------------------
st.markdown("""
<div class="main-header">
    <h1>🛍️ ShopSmart Customer Support</h1>
    <p>Multi-Agent System — Powered by LangGraph</p>
</div>
""", unsafe_allow_html=True)

tab_chat, tab_manager, tab_dashboard, tab_protocols, tab_observability = st.tabs([
    "💬 Chat", "👤 Manager Review", "📊 Dashboard", "🔌 Protocol Benchmark", "🔍 Observability"
])


# ---------------------------------------------------------------------------
# Tab 1: Chat
# ---------------------------------------------------------------------------
with tab_chat:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Enter your support request...", disabled=not st.session_state.system_ready):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Processing your request..."):
                graph, memory, store, data, known_names, lf_handler, metrics = st.session_state.system

                from shopsmart.pii import redact_pii
                redacted_text, pii_mapping = redact_pii(
                    prompt, None, data["customers_db"], known_names
                )

                ticket_id = f"ST-{uuid.uuid4().hex[:6].upper()}"

                initial_state = {
                    "messages": [HumanMessage(content=redacted_text)],
                    "ticket_id": ticket_id,
                    "customer_id": "CUST-0001",
                    "customer_tier": "bronze",
                    "ticket_text": prompt,
                    "redacted_text": redacted_text,
                    "category": "",
                    "priority": "",
                    "classification_confidence": 0.0,
                    "specialist_response": "",
                    "needs_escalation": False,
                    "human_notes": "",
                    "final_response": "",
                    "tools_used": [],
                    "pii_mapping": pii_mapping,
                }

                config = {"configurable": {"thread_id": st.session_state.thread_id}}

                start = time.time()
                try:
                    result = graph.invoke(initial_state, config)
                    latency = time.time() - start

                    response = result.get("final_response", "No response generated.")
                    category = result.get("category", "unknown")
                    priority = result.get("priority", "unknown")

                    # Check for escalation
                    if result.get("needs_escalation"):
                        st.session_state.escalation_queue.append({
                            "ticket_id": ticket_id,
                            "text": prompt,
                            "category": category,
                            "priority": priority,
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        })
                        st.warning("⚠️ This ticket has been escalated to a manager for review.")

                    st.markdown(response)

                    with st.expander("📋 Ticket Details"):
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Category", category)
                        col2.metric("Priority", priority)
                        col3.metric("Latency", f"{latency:.1f}s")
                        st.caption(f"Tools: {', '.join(result.get('tools_used', []))}")

                    # Update metrics
                    m = st.session_state.metrics_data
                    m["total"] += 1
                    m["categories"][category] = m["categories"].get(category, 0) + 1
                    m["latencies"].append(latency)
                    if result.get("needs_escalation"):
                        m["escalations"] += 1
                    if "quick_answer" in str(result.get("tools_used", [])):
                        m["quick_answers"] += 1

                except Exception as e:
                    response = f"Error processing request: {str(e)}"
                    st.error(response)

                st.session_state.messages.append({"role": "assistant", "content": response})

    if not st.session_state.system_ready:
        st.info("👈 Click 'Initialize System' in the sidebar to begin.")


# ---------------------------------------------------------------------------
# Tab 2: Manager Review (HITL)
# ---------------------------------------------------------------------------
with tab_manager:
    st.subheader("Escalation Queue")

    if not st.session_state.escalation_queue:
        st.info("No tickets pending review.")
    else:
        for i, esc in enumerate(st.session_state.escalation_queue):
            st.markdown(f"""
            <div class="escalation-card">
                <strong>Ticket {esc['ticket_id']}</strong> — {esc['category']} ({esc['priority']})
                <br/><small>{esc['timestamp']}</small>
                <br/><em>{esc['text'][:200]}...</em>
            </div>
            """, unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✅ Approve", key=f"approve_{i}"):
                    st.session_state.escalation_queue.pop(i)
                    st.success("Ticket approved.")
                    st.rerun()
            with col2:
                if st.button("✏️ Modify", key=f"modify_{i}"):
                    st.text_area("Manager Notes", key=f"notes_{i}")
            with col3:
                if st.button("❌ Reject", key=f"reject_{i}"):
                    st.session_state.escalation_queue.pop(i)
                    st.warning("Ticket rejected.")
                    st.rerun()


# ---------------------------------------------------------------------------
# Tab 3: Dashboard
# ---------------------------------------------------------------------------
with tab_dashboard:
    st.subheader("System Metrics")
    m = st.session_state.metrics_data

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tickets", m["total"])
    col2.metric("Escalations", m["escalations"])
    col3.metric("Quick Answers", m["quick_answers"])
    avg_lat = sum(m["latencies"]) / len(m["latencies"]) if m["latencies"] else 0
    col4.metric("Avg Latency", f"{avg_lat:.1f}s")

    if m["categories"]:
        st.subheader("Category Distribution")
        import pandas as pd
        df = pd.DataFrame(
            list(m["categories"].items()),
            columns=["Category", "Count"],
        )
        st.bar_chart(df.set_index("Category"))

    if m["latencies"]:
        st.subheader("Latency Over Time")
        st.line_chart(m["latencies"])

    st.subheader("System Architecture")
    st.markdown("""
    | Component | Details |
    |-----------|---------|
    | Graph Nodes | 8 (supervisor + 5 handlers + escalation + formatter) |
    | Specialist Agents | 4 (order, returns, billing, product) |
    | Tools | 10 (MCP-enabled) |
    | Primary LLM | gpt-5-mini |
    | Secondary LLM | gpt-4.1-mini (temp=0.3) |
    | RAG | FAISS + text-embedding-3-small |
    | Memory | MemorySaver (thread) + InMemoryStore (cross-session) |
    | Protocols | MCP (tools) + A2A (inter-agent) |
    | Observability | LangSmith + Langfuse |
    """)


# ---------------------------------------------------------------------------
# Tab 4: Protocol Benchmark
# ---------------------------------------------------------------------------
with tab_protocols:
    st.subheader("Communication Protocol Benchmark")
    st.caption(
        "Compares all 10 protocols (REST, GraphQL, gRPC, Webhook, WebSocket, MQTT, AMQP, "
        "SOAP, MCP, A2A) on latency, payload size, and error/retry behavior — measured live, "
        "inside the specialist agents' real tool-calling loop, not a synthetic isolated test."
    )

    if not st.session_state.system_ready:
        st.info("Waiting for the system to finish loading (see sidebar)...")
    else:
        graph, memory, store, data, known_names, lf_handler, metrics = st.session_state.system

        col_a, col_b = st.columns([1, 3])
        with col_a:
            num_tickets = st.number_input("Tickets to process", min_value=1, max_value=50, value=8)
            run_clicked = st.button("▶️ Run benchmark", type="primary")
        with col_b:
            st.caption(
                "Runs N sample tickets end-to-end through the graph so each specialist "
                "exercises its bound protocol tools (REST/WS in order_specialist, GraphQL/gRPC/"
                "MQTT/SOAP in product_specialist, AMQP/MCP in billing_specialist, Webhook/A2A "
                "in returns_specialist). Requires `make protocols-up` (and `make brokers-up` + "
                "`make responders-up` for MQTT/AMQP) running in a separate terminal."
            )

        if run_clicked:
            progress = st.progress(0.0, text="Starting protocol benchmark...")
            from shopsmart.data_loader import select_benchmark_tickets

            tickets = select_benchmark_tickets(data["tickets"], int(num_tickets))
            for i, ticket in enumerate(tickets):
                progress.progress(
                    (i) / max(len(tickets), 1),
                    text=f"Processing ticket {i + 1}/{len(tickets)}: {ticket['ticket_id']}...",
                )
                try:
                    from shopsmart.graph import process_ticket

                    process_ticket(ticket, graph, data, known_names, langfuse_handler=lf_handler)
                except Exception as exc:
                    st.warning(f"Ticket {ticket['ticket_id']} failed: {exc}")
            progress.progress(1.0, text="Done.")

            # Mirror `benchmark_runner.py`'s terminal + file artifacts so a UI-driven
            # run produces the same summary/JSON/chart as the CLI benchmark.
            print()
            print("[Streamlit Protocol Benchmark] Run complete -- summary below\n")
            metrics.print_summary()
            from shopsmart.config import get_output_dir

            report_path = get_output_dir() / "protocol_benchmark_report.json"
            with open(report_path, "w") as f:
                f.write(metrics.export_json())
            print(f"[Streamlit Protocol Benchmark] Full metrics JSON written to {report_path}")
            if metrics.protocol_stats:
                from shopsmart.charts import plot_protocol_comparison

                plot_protocol_comparison(metrics.protocol_stats)

        stats = metrics.protocol_stats
        if not stats:
            st.info("No protocol calls recorded yet — click **Run benchmark** above, or use the Chat tab.")
        else:
            import pandas as pd

            rows = []
            for protocol, s in sorted(stats.items()):
                rows.append(
                    {
                        "Protocol": protocol,
                        "Calls": s["call_count"],
                        "p50 (ms)": s["p50_latency_ms"],
                        "p95 (ms)": s["p95_latency_ms"],
                        "Avg Payload (B)": s["avg_payload_bytes"],
                        "Error %": s["error_rate"],
                        "Retry %": s["retry_rate"],
                    }
                )
            df = pd.DataFrame(rows)
            st.dataframe(df, width="stretch", hide_index=True)

            st.subheader("Latency comparison (p50 vs p95)")
            st.bar_chart(df.set_index("Protocol")[["p50 (ms)", "p95 (ms)"]])

            st.subheader("Payload size comparison")
            st.bar_chart(df.set_index("Protocol")[["Avg Payload (B)"]])

            missing = sorted(
                set(
                    [
                        "REST", "GRAPHQL", "GRPC", "WEBHOOK", "WS",
                        "MQTT", "AMQP", "SOAP", "MCP", "A2A",
                    ]
                )
                - set(stats.keys())
            )
            if missing:
                st.caption(f"Not yet exercised in this session: {', '.join(missing)}")


# ---------------------------------------------------------------------------
# Tab 5: Observability
# ---------------------------------------------------------------------------
with tab_observability:
    st.subheader("Observability Configuration")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### LangSmith")
        if os.getenv("LANGSMITH_API_KEY"):
            st.success("✅ Auto-tracing enabled")
            st.caption(f"Project: {os.getenv('LANGSMITH_PROJECT', 'shopsmart-support')}")
            st.markdown("[Open LangSmith Dashboard →](https://smith.langchain.com/)")
        else:
            st.warning("Not configured. Set LANGSMITH_API_KEY in .env")

    with col2:
        st.markdown("### Langfuse")
        if os.getenv("LANGFUSE_PUBLIC_KEY"):
            st.success("✅ Callback tracing enabled")
            st.caption(f"Host: {os.getenv('LANGFUSE_HOST', 'https://us.cloud.langfuse.com')}")
            st.markdown("[Open Langfuse Dashboard →](https://us.cloud.langfuse.com)")
        else:
            st.warning("Not configured. Set LANGFUSE keys in .env")

    st.markdown("---")
    st.subheader("Patterns Implemented")
    patterns = [
        "Supervisor Router (structured output)",
        "Specialist Sub-Agents (tool-calling)",
        "Deterministic Quick-Answer (no LLM)",
        "RAG Policy Lookup (FAISS)",
        "PII Redaction/Restoration",
        "HITL Escalation (interrupt/resume)",
        "Thread Memory (MemorySaver)",
        "Cross-Session Store (InMemoryStore)",
        "MCP Protocol (10 tools)",
        "A2A Protocol (Google spec)",
        "Observability (LangSmith + Langfuse)",
    ]
    for p in patterns:
        st.markdown(f"✅ {p}")
