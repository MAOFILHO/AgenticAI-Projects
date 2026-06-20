"""Visualization: latency comparison, routing distribution, and tool usage."""

from collections import Counter


def plot_comparison(langsmith_results: list[dict], langfuse_results: list[dict]) -> None:
    """Render side-by-side latency bar chart and category pie chart."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("[Charts] matplotlib not installed — skipping plots.")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    tickets = [r["ticket"] for r in langsmith_results]
    ls_lat = [r["latency_s"] for r in langsmith_results]
    lf_lat = [r["latency_s"] for r in langfuse_results]

    x = range(len(tickets))
    width = 0.35
    ax1.bar([i - width / 2 for i in x], ls_lat, width, label="LangSmith", color="#0F62FE")
    ax1.bar([i + width / 2 for i in x], lf_lat, width, label="Langfuse", color="#FF6F00")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(tickets)
    ax1.set_ylabel("Latency (seconds)")
    ax1.set_title("Latency per Ticket: Both Platforms")
    ax1.legend()
    ax1.grid(axis="y", alpha=0.3)

    categories = [r["category"] for r in langsmith_results]
    cat_counts = Counter(categories)
    ax2.pie(
        cat_counts.values(),
        labels=cat_counts.keys(),
        autopct="%1.0f%%",
        colors=["#2196F3", "#FF9800", "#4CAF50", "#9C27B0"],
    )
    ax2.set_title("Ticket Category Distribution")

    plt.suptitle("ShopSmart Observability Report", fontweight="bold")
    plt.tight_layout()
    plt.savefig("observability_report.png", dpi=150, bbox_inches="tight")
    plt.show()
    print("[Charts] Saved → observability_report.png")


def print_comparison_table(langsmith_results: list[dict], langfuse_results: list[dict]) -> None:
    """Print a plain-text comparison table to stdout."""
    print("\nMetrics Comparison: LangSmith vs Langfuse")
    print("=" * 80)
    print(f"{'Ticket':<10} {'Category':<15} {'LS Latency':<12} {'LF Latency':<12} {'Resp Chars':<12}")
    print("-" * 80)
    for ls, lf in zip(langsmith_results, langfuse_results):
        print(
            f"{ls['ticket']:<10} {ls['category']:<15} "
            f"{ls['latency_s']:<12.2f} {lf['latency_s']:<12.2f} "
            f"{ls['response_chars']:<12}"
        )
    ls_avg = sum(r["latency_s"] for r in langsmith_results) / len(langsmith_results)
    lf_avg = sum(r["latency_s"] for r in langfuse_results) / len(langfuse_results)
    print("-" * 80)
    print(f"{'AVG':<10} {'':<15} {ls_avg:<12.2f} {lf_avg:<12.2f}")


def plot_routing_distribution(category_counts: dict) -> None:
    """Plot routing category distribution pie chart."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return

    fig, ax = plt.subplots(figsize=(8, 6))
    colors = ["#2196F3", "#FF9800", "#4CAF50", "#9C27B0", "#F44336", "#607D8B"]
    ax.pie(
        category_counts.values(),
        labels=category_counts.keys(),
        autopct="%1.1f%%",
        colors=colors[: len(category_counts)],
    )
    ax.set_title("Ticket Routing Distribution", fontweight="bold")
    plt.tight_layout()
    plt.savefig("routing_distribution.png", dpi=150, bbox_inches="tight")
    plt.show()


def plot_tool_usage(tool_usage: dict) -> None:
    """Plot tool usage horizontal bar chart."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return

    sorted_tools = sorted(tool_usage.items(), key=lambda x: x[1])
    names = [t[0] for t in sorted_tools]
    counts = [t[1] for t in sorted_tools]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(names, counts, color="#0F62FE")
    ax.set_xlabel("Invocations")
    ax.set_title("Tool Usage Frequency", fontweight="bold")
    plt.tight_layout()
    plt.savefig("tool_usage.png", dpi=150, bbox_inches="tight")
    plt.show()
