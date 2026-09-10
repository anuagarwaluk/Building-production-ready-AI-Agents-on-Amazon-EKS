"""AnyCompany Shop MCP server.

The tool access lab moves business tools out of the agent and behind the
Model Context Protocol. Three tools, one server, shared by every agent
that needs them:

  lookup_order(order_id)          order status, items, totals, tracking
  check_inventory(product_name)   stock level and restock ETA
  process_return(order_id, reason) start a return under the 30 day policy

Runs over stdio for local development or streamable HTTP (:8080/mcp) as a
Kubernetes service. Data comes from the JSON files in /app/data.
"""

import argparse
import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("anycompany-shop-tools")

_DATA_DIR_CANDIDATES = [
    os.getenv("DATA_DIR", ""),
    "/app/data",
    str(Path(__file__).resolve().parents[2] / "data"),
]


def _load(name: str) -> dict:
    for base in _DATA_DIR_CANDIDATES:
        path = os.path.join(base, name) if base else ""
        if path and os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    raise FileNotFoundError(f"{name} not found in {_DATA_DIR_CANDIDATES}")


ORDERS = _load("orders.json")
INVENTORY = _load("inventory.json")
RETURNS: dict[str, dict] = {}


@mcp.tool()
def lookup_order(order_id: str) -> str:
    """Look up an order by ID: status, items, totals, tracking, delivery.

    Args:
        order_id: The order identifier, e.g. ORD-12345
    """
    order = ORDERS.get(order_id.strip().upper())
    if not order:
        return f"No order found with ID {order_id}."
    return json.dumps(order, indent=2)


@mcp.tool()
def check_inventory(product_name: str) -> str:
    """Check stock availability for a product.

    Args:
        product_name: Product name, e.g. "USB-C Hub"
    """
    needle = product_name.strip().lower()
    matches = {
        name: info for name, info in INVENTORY.items() if needle in name.lower()
    }
    if not matches:
        return f"No inventory record matching '{product_name}'."
    lines = []
    for name, info in matches.items():
        if info["in_stock"] > 0:
            lines.append(f"{name}: {info['in_stock']} in stock ({info['warehouse']})")
        else:
            eta = info.get("restock_eta") or "unknown"
            lines.append(f"{name}: out of stock, restock expected {eta}")
    return "\n".join(lines)


@mcp.tool()
def process_return(order_id: str, reason: str) -> str:
    """Start a return for an order under the 30 day returns policy.

    Args:
        order_id: The order to return, e.g. ORD-67890
        reason: The customer's reason for the return
    """
    order = ORDERS.get(order_id.strip().upper())
    if not order:
        return f"Cannot start a return: no order found with ID {order_id}."
    if order["status"] not in ("Delivered", "Shipped"):
        return (
            f"Order {order_id} is still {order['status']}. It can be cancelled "
            "instead of returned; a return starts after delivery."
        )
    rma = f"RMA-{abs(hash(order_id + reason)) % 100000:05d}"
    RETURNS[rma] = {"order_id": order_id, "reason": reason, "status": "Label emailed"}
    return (
        f"Return started for {order_id}. RMA number {rma}. A prepaid label has "
        "been emailed; refunds are issued within 5 business days of the item "
        "arriving back."
    )


def main():
    parser = argparse.ArgumentParser(description="AnyCompany Shop MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="streamable-http",
    )
    args = parser.parse_args()
    print(f"Starting shop MCP server ({args.transport})")
    mcp.settings.port = int(os.getenv("MCP_PORT", "8080"))
    mcp.settings.host = "0.0.0.0"
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
