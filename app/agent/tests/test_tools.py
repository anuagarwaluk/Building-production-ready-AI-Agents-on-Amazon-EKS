"""Order lookup tool behaviour, no model or network required."""

import json

from src.tools import ORDERS, lookup_order


def test_known_order_returns_details():
    result = lookup_order("ORD-12345")
    data = json.loads(result)
    assert data["customer"] == "Jane Doe"
    assert data["status"] == "Shipped"


def test_lookup_is_case_and_whitespace_tolerant():
    result = lookup_order("  ord-67890 ")
    data = json.loads(result)
    assert data["status"] == "Delivered"


def test_unknown_order_lists_known_ids():
    result = lookup_order("ORD-99999")
    assert "No order found" in result
    for order_id in ORDERS:
        assert order_id in result


def test_the_three_workshop_orders_exist():
    assert {"ORD-12345", "ORD-67890", "ORD-11111"} <= set(ORDERS.keys())
