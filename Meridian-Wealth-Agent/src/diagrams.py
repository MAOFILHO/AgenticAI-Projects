"""
Generate and save LangGraph architecture diagrams as PNG files to the /output folder.
Two diagrams are produced:
  1. react_architecture.png  — custom graphviz diagram of the ReAct loop + tools
  2. langgraph_agent.png     — native LangGraph Mermaid render of the compiled graph
"""

import os
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def save_react_architecture_diagram():
    """Build and save a Graphviz diagram of the agent architecture."""
    try:
        from graphviz import Digraph
    except ImportError:
        print("⚠️  graphviz Python package not installed — skipping react_architecture.png")
        return None

    dot = Digraph("financial_react", format="png")
    dot.attr(rankdir="TB", splines="spline", nodesep="0.55", ranksep="0.7")
    dot.attr(bgcolor="white")

    edge_color = "#666666"
    node_outline = "#8E7CC3"
    node_fill = "#F3F0FA"
    tool_fill = "#E8F5E9"
    tool_outline = "#4CAF50"

    dot.attr(
        "node",
        style="rounded,filled",
        color=node_outline,
        fillcolor=node_fill,
        fontname="Helvetica",
        fontsize="13",
        penwidth="1.6",
        margin="0.22,0.14",
    )

    # Main nodes
    dot.node("user", "👤 User Query", shape="oval")
    dot.node("model", "🧠 LLM / ReAct Agent\n(gpt-5-mini)", shape="box")
    dot.node("answer", "✅ Final Answer", shape="oval")

    # Tool cluster
    with dot.subgraph(name="cluster_tools") as s:
        s.attr(
            label="🔧 Agent Tools",
            style="rounded,filled",
            color="#CCBBEE",
            fillcolor="#FAF8FF",
            fontname="Helvetica",
            fontsize="12",
        )
        s.node(
            "tools",
            "portfolio_lookup\nmarket_data_search\ncalculate_metrics\npolicy_retriever\ntavily_search",
            shape="box",
            fillcolor=tool_fill,
            color=tool_outline,
        )

    # Data sources cluster
    with dot.subgraph(name="cluster_data") as s:
        s.attr(
            label="🗄️ Data Sources",
            style="rounded,filled",
            color="#BBDDEE",
            fillcolor="#F5FAFF",
            fontname="Helvetica",
            fontsize="12",
        )
        s.node("sqlite", "SQLite DB\nclients · holdings\nmarket_data", shape="cylinder", fillcolor="#E3F2FD", color="#1565C0")
        s.node("faiss", "FAISS Vector Store\n5 Policy PDFs\n(RAG)", shape="cylinder", fillcolor="#FFF8E1", color="#F57F17")
        s.node("web", "Tavily Web Search\n(live news)", shape="cylinder", fillcolor="#FCE4EC", color="#C62828")

    dot.edge("user", "model", color=edge_color)
    dot.edge("model", "tools", label="action", color=edge_color)
    dot.edge("tools", "model", label="observation", color=edge_color)
    dot.edge("model", "answer", style="dashed", color=edge_color, label="stop")
    dot.edge("tools", "sqlite", style="dotted", color="#1565C0")
    dot.edge("tools", "faiss", style="dotted", color="#F57F17")
    dot.edge("tools", "web", style="dotted", color="#C62828")

    out_path = str(OUTPUT_DIR / "react_architecture")
    saved = dot.render(out_path, cleanup=True)
    print(f"✅ Saved: {saved}")
    return saved


def save_langgraph_diagram(agent):
    """Render the native LangGraph compiled graph as a Mermaid PNG."""
    try:
        png_bytes = agent.get_graph().draw_mermaid_png()
        out_path = OUTPUT_DIR / "langgraph_agent.png"
        with open(out_path, "wb") as f:
            f.write(png_bytes)
        print(f"✅ Saved: {out_path}")
        return str(out_path)
    except Exception as e:
        print(f"⚠️  Could not render LangGraph Mermaid PNG: {e}")
        print("   (Requires 'pip install mermaid-py' or access to mermaid.ink)")
        return None


def generate_all_diagrams(agent=None):
    print("\n📊 Generating architecture diagrams → output/")
    path1 = save_react_architecture_diagram()
    path2 = save_langgraph_diagram(agent) if agent else None
    print(f"\nDiagrams saved to: {OUTPUT_DIR}")
    return path1, path2
