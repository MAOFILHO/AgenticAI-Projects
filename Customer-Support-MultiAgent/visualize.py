"""
visualize.py — Visualize the compiled LangGraph StateGraph.

Saves the architecture diagram as a PNG to the output/ folder.
Falls back to printing Mermaid text if the PNG renderer is unavailable.

PNG rendering requires one of:
    pip install playwright && playwright install chromium
    -- or --
    pip install pyppeteer

If neither is installed the Mermaid source is printed instead,
which can be pasted into https://mermaid.live to view the diagram.
"""
from __future__ import annotations

import os
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
PNG_PATH = OUTPUT_DIR / "graph_architecture.png"
MERMAID_PATH = OUTPUT_DIR / "graph_architecture.md"


def visualize_graph(graph) -> None:
    """
    Generate and save the graph architecture diagram.

    Tries PNG first (requires playwright or pyppeteer).
    Falls back to saving Mermaid markdown + printing to terminal.

    Args:
        graph: Compiled LangGraph returned by graph.build_graph()
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("GRAPH ARCHITECTURE VISUALIZATION")
    print("=" * 60)

    # ── Attempt 1: PNG via draw_mermaid_png ──────────────────
    try:
        png_bytes = graph.get_graph().draw_mermaid_png()
        with open(PNG_PATH, "wb") as f:
            f.write(png_bytes)
        print(f"  [OK] PNG saved → {PNG_PATH}")
        _print_mermaid_text(graph)
        return
    except Exception as png_err:
        print(f"  [INFO] PNG rendering unavailable: {png_err}")
        print("         Install with: pip install playwright && playwright install chromium")

    # ── Fallback: Mermaid text ────────────────────────────────
    _print_mermaid_text(graph)
    _save_mermaid_markdown(graph)


def _get_mermaid_text(graph) -> str:
    try:
        return graph.get_graph().draw_mermaid()
    except Exception as e:
        return f"# Could not generate Mermaid diagram: {e}"


def _print_mermaid_text(graph) -> None:
    mermaid = _get_mermaid_text(graph)
    print("\n  Mermaid diagram (paste into https://mermaid.live):\n")
    print("  " + "\n  ".join(mermaid.splitlines()))


def _save_mermaid_markdown(graph) -> None:
    mermaid = _get_mermaid_text(graph)
    content = (
        "# ShopSmart Multi-Agent Graph Architecture\n\n"
        "Paste the diagram below into https://mermaid.live to view.\n\n"
        "```mermaid\n"
        f"{mermaid}\n"
        "```\n"
    )
    with open(MERMAID_PATH, "w") as f:
        f.write(content)
    print(f"\n  [OK] Mermaid markdown saved → {MERMAID_PATH}")
