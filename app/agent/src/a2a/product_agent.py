"""Product and sandbox specialist.

Owns product knowledge (Milvus RAG, and the Neo4j graph when configured)
plus, on the integrated track, the sandboxed tools: Code Interpreter for
computation and the managed Browser for live pages. The workshop calls
this the Product/Sandbox Agent.
"""

import logging
import os
import sys
from typing import Any, List

from strands import Agent

from ..agent import build_model
from .serving import serve_a2a

logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") == "1" else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)


def product_agent() -> Agent:
    tools: List[Any] = []
    if os.getenv("MILVUS_URI"):
        from ..rag import search_products

        tools.append(search_products)
    if os.getenv("NEO4J_URI"):
        from ..kg import related_products

        tools.append(related_products)
    if os.getenv("AGENTCORE_TOOLS") == "1":
        from ..sandbox import browse_url, execute_python

        tools.extend([execute_python, browse_url])

    return Agent(
        name="Product Agent",
        agent_id="product_agent",
        description=(
            "Product specialist for AnyCompany Shop: catalogue and policy "
            "questions, product recommendations, and safe computation"
        ),
        model=build_model(),
        system_prompt="""
        You are the product specialist for AnyCompany Shop. You answer
        product and store policy questions from the catalogue tools, and
        you perform precise computation with the code tool when available.
        Ground every claim in a tool result.
        """,
        tools=tools,
    )


def main():
    serve_a2a(product_agent())


if __name__ == "__main__":
    main()
