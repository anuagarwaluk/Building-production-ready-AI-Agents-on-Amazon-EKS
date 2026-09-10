"""Order specialist: everything transactional, nothing else.

Owns order lookups, inventory checks, and returns through the shop MCP
server. Splitting this out means the tools that touch order data live
behind one agent with one narrow job, which is easier to secure, test,
and evaluate than a generalist.
"""

import logging
import os
import sys

from strands import Agent

from ..agent import build_model, build_tools
from .serving import serve_a2a

logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") == "1" else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)


def order_agent() -> Agent:
    # Force MCP tools for this specialist regardless of the default
    os.environ.setdefault("ORDERS_TOOL_MODE", "mcp")
    return Agent(
        name="Order Agent",
        agent_id="order_agent",
        description=(
            "Order specialist for AnyCompany Shop: order status and tracking "
            "lookups, inventory checks, and processing return requests"
        ),
        model=build_model(),
        system_prompt="""
        You are the order specialist for AnyCompany Shop. You handle order
        status, tracking, delivery estimates, inventory availability, and
        returns. Always use your tools; never invent order details. Answer
        only order and inventory questions and answer them completely.
        """,
        tools=build_tools(),
    )


def main():
    serve_a2a(order_agent())


if __name__ == "__main__":
    main()
