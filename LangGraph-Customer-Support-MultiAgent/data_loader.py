"""
data_loader.py — Load all ShopSmart data files and build O(1) lookup indexes.
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def load_all() -> dict:
    """
    Load all data files and return a dict of indexed databases.

    Returns:
        {
          "CUSTOMERS_DB":    {customer_id: customer_dict},
          "ORDERS_DB":       {order_id: order_dict},
          "PRODUCTS_DB":     {product_id: product_dict},
          "CUSTOMER_ORDERS": {customer_id: [order_dict, ...]},
          "TICKETS":         [ticket_dict, ...],
          "POLICIES":        str (raw markdown),
        }
    """
    with open(DATA_DIR / "customers.json") as f:
        customers_raw = json.load(f)
    with open(DATA_DIR / "orders.json") as f:
        orders_raw = json.load(f)
    with open(DATA_DIR / "products.json") as f:
        products_raw = json.load(f)
    with open(DATA_DIR / "tickets.json") as f:
        tickets = json.load(f)
    with open(DATA_DIR / "policies.md") as f:
        policies = f.read()

    customers_db = {c["customer_id"]: c for c in customers_raw}
    orders_db = {o["order_id"]: o for o in orders_raw}
    products_db = {p["product_id"]: p for p in products_raw}

    customer_orders: dict[str, list] = {}
    for order in orders_raw:
        cid = order["customer_id"]
        customer_orders.setdefault(cid, []).append(order)

    return {
        "CUSTOMERS_DB": customers_db,
        "ORDERS_DB": orders_db,
        "PRODUCTS_DB": products_db,
        "CUSTOMER_ORDERS": customer_orders,
        "TICKETS": tickets,
        "POLICIES": policies,
    }


def print_summary(data: dict) -> None:
    """Print data loading summary."""
    print("=" * 60)
    print("DATA LOADED SUCCESSFULLY")
    print("=" * 60)
    print(f"Customers:  {len(data['CUSTOMERS_DB']):>4} records")
    print(f"Orders:     {len(data['ORDERS_DB']):>4} records")
    print(f"Products:   {len(data['PRODUCTS_DB']):>4} records")
    print(f"Tickets:    {len(data['TICKETS']):>4} records")
    print(f"Policies:   {len(data['POLICIES']):>4} characters")

    tier_counts: dict[str, int] = {}
    for c in data["CUSTOMERS_DB"].values():
        tier_counts[c["tier"]] = tier_counts.get(c["tier"], 0) + 1
    print("\nCustomer Tier Distribution:")
    for tier, count in sorted(tier_counts.items()):
        print(f"  {tier:>10}: {count}")

    cat_counts: dict[str, int] = {}
    for t in data["TICKETS"]:
        cat_counts[t["category"]] = cat_counts.get(t["category"], 0) + 1
    print("\nTicket Category Distribution:")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat:>18}: {count}")

    status_counts: dict[str, int] = {}
    for o in data["ORDERS_DB"].values():
        status_counts[o["status"]] = status_counts.get(o["status"], 0) + 1
    print("\nOrder Status Distribution:")
    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        print(f"  {status:>12}: {count}")
