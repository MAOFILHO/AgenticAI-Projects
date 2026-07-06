"""Load JSON datasets and policies from the data directory."""

import json
from collections import defaultdict
from pathlib import Path


def load_all(data_dir: Path | str) -> dict:
    """
    Load all data files and return a dict with keyed databases.

    Returns:
        {
            "customers_db": {customer_id: record},
            "orders_db": {order_id: record},
            "products_db": {product_id: record},
            "tickets": [list of ticket dicts],
            "customer_orders": {customer_id: [orders]},
            "policies_text": str,
        }
    """
    data_dir = Path(data_dir)

    with open(data_dir / "customers.json") as f:
        customers_raw = json.load(f)
    customers_db = {c["customer_id"]: c for c in customers_raw}

    with open(data_dir / "orders.json") as f:
        orders_raw = json.load(f)
    orders_db = {o["order_id"]: o for o in orders_raw}

    with open(data_dir / "products.json") as f:
        products_raw = json.load(f)
    products_db = {p["product_id"]: p for p in products_raw}

    with open(data_dir / "tickets.json") as f:
        tickets = json.load(f)

    with open(data_dir / "policies.md") as f:
        policies_text = f.read()

    customer_orders: dict[str, list] = defaultdict(list)
    for order in orders_raw:
        customer_orders[order["customer_id"]].append(order)

    return {
        "customers_db": customers_db,
        "orders_db": orders_db,
        "products_db": products_db,
        "tickets": tickets,
        "customer_orders": dict(customer_orders),
        "policies_text": policies_text,
    }


def select_benchmark_tickets(tickets: list[dict], num_tickets: int) -> list[dict]:
    """
    Pick `num_tickets` tickets, round-robin across categories so every
    category (and thus every specialist/protocol it owns) gets a shot as
    early as possible, instead of relying on the tickets' original file
    order (which is heavily skewed toward order_status).
    """
    by_category: dict[str, list[dict]] = defaultdict(list)
    for t in tickets:
        by_category[t.get("category", "unknown")].append(t)

    selected: list[dict] = []
    cursors = dict.fromkeys(by_category, 0)
    while len(selected) < num_tickets and any(
        cursors[cat] < len(bucket) for cat, bucket in by_category.items()
    ):
        for cat, bucket in by_category.items():
            if len(selected) >= num_tickets:
                break
            i = cursors[cat]
            if i < len(bucket):
                selected.append(bucket[i])
                cursors[cat] = i + 1

    return selected
