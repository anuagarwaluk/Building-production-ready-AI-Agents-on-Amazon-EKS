"""Lab 1 tool: order lookup against local data.

This is where the workshop starts: a single hardcoded capability so the
agent loop itself is the only new thing. In the MCP lab the same lookup
moves behind an MCP server (app/mcp-server) and this local tool is switched
off with ORDERS_TOOL_MODE=mcp. Nothing else about the agent changes.
"""

import json
import os
from pathlib import Path

from strands import tool

_DATA_CANDIDATES = [
    os.getenv("ORDERS_FILE", ""),
    "/app/data/orders.json",
    str(Path(__file__).resolve().parents[3] / "data" / "orders.json"),
]


def _load_orders() -> dict:
    for candidate in _DATA_CANDIDATES:
        if candidate and os.path.exists(candidate):
            with open(candidate) as f:
                return json.load(f)
    # Last resort: the three workshop orders, inline
    return {
        "ORD-12345": {"order_id": "ORD-12345", "customer": "Jane Doe", "status": "Shipped", "total": 1299.99, "items": [{"product": "Laptop Pro 15", "quantity": 1, "unit_price": 1299.99}]},
        "ORD-67890": {"order_id": "ORD-67890", "customer": "John Smith", "status": "Delivered", "total": 129.97, "items": [{"product": "Wireless Mouse", "quantity": 1, "unit_price": 29.99}, {"product": "USB-C Hub", "quantity": 2, "unit_price": 49.99}]},
        "ORD-11111": {"order_id": "ORD-11111", "customer": "Alice Johnson", "status": "Processing", "total": 249.99, "items": [{"product": "Noise Cancelling Headphones", "quantity": 1, "unit_price": 249.99}]},
    }


ORDERS = _load_orders()


@tool
def lookup_order(order_id: str) -> str:
    """Look up an order by its order ID and return status, items, totals,
    and tracking details when available.

    Args:
        order_id: The order identifier, e.g. ORD-12345
    """
    order = ORDERS.get(order_id.strip().upper())
    if not order:
        known = ", ".join(sorted(ORDERS.keys()))
        return f"No order found with ID {order_id}. Known test orders: {known}."
    return json.dumps(order, indent=2)
