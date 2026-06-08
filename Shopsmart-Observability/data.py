"""ShopSmart static data: orders DB and support policies."""

ORDERS_DB = {
    "ORD-1001": {
        "customer": "Priya Sharma",
        "item": "Samsung Galaxy S24",
        "amount": "₹74,999",
        "status": "In Transit",
        "city": "Mumbai",
        "expected_delivery": "2 days",
    },
    "ORD-1002": {
        "customer": "Rahul Verma",
        "item": "Sony WH-1000XM5",
        "amount": "₹24,990",
        "status": "Delivered",
        "city": "Delhi",
        "expected_delivery": "Delivered on 8 Apr",
    },
    "ORD-1003": {
        "customer": "Anita Desai",
        "item": "MacBook Air M3",
        "amount": "₹1,14,900",
        "status": "Processing",
        "city": "Bangalore",
        "expected_delivery": "5 days",
    },
}

RETURN_POLICY = (
    "7-day return for electronics, 15-day for clothing. "
    "Refund in 5-7 business days."
)

BILLING_POLICY = (
    "UPI, Cards, Net Banking, Wallet. "
    "Failed payment refund: 3-5 days. "
    "EMI on orders above ₹3,000."
)

TEST_TICKETS = [
    {"id": "TKT-001", "query": "What's the status of order ORD-1001?"},
    {"id": "TKT-002", "query": "I want to return my Sony headphones from ORD-1002."},
    {"id": "TKT-003", "query": "What EMI options are available for the MacBook?"},
    {"id": "TKT-004", "query": "Tell me more about the Samsung Galaxy S24."},
    {"id": "TKT-005", "query": "When will my order ORD-1003 be delivered to Bangalore?"},
]
