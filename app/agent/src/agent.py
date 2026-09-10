"""AnyCompany Shop customer service agent.

One agent, assembled from capabilities that are each switched by
configuration. This mirrors how the workshop layers labs on top of each
other, and it is the whole thesis of the repo: the agent code is identical
across the self-managed and integrated tracks; only the environment differs.

  Capability          Env switch                     Self-managed        Integrated
  Model               MODEL_ID (via LiteLLM)         qwen2-5-3b-neuron   nova-lite
  Order tools         ORDERS_TOOL_MODE=local|mcp     MCP server on EKS   MCP server on EKS
  Product knowledge   MILVUS_URI set                 Milvus RAG          Milvus RAG
  Knowledge graph     NEO4J_URI set                  Neo4j               (optional)
  Sandboxed tools     AGENTCORE_TOOLS=1              n/a                 Code Interpreter + Browser
  Memory              MEMORY_BACKEND (server.py)     milvus              agentcore

The model is always reached through the LiteLLM proxy, which speaks the
OpenAI API. Swapping a self-hosted vLLM model for Amazon Bedrock is a
change to MODEL_ID and nothing else.

Built from my hands-on run of the AWS "AI Agents on Amazon EKS" workshop.
"""

import logging
import os
import sys
from typing import Any, List

from strands import Agent
from strands.models.openai import OpenAIModel

logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") == "1" else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are the customer service agent for AnyCompany Shop, an online store for
electronics and accessories. Help customers with:
- Order status, tracking numbers, and delivery estimates (always use the
  order lookup tool; never invent order details)
- Product questions, using the product knowledge tool when available
- Inventory and stock availability
- Return requests, following the 30 day returns policy
- Light computation such as totalling orders (use the code execution tool
  when precise arithmetic matters and it is available)

Ground every factual claim in a tool result. If a tool returns nothing,
say so rather than guessing. Be concise, warm, and practical.
"""


def build_model() -> OpenAIModel:
    """The one URL agents talk to: the LiteLLM proxy."""
    base_url = os.getenv("LITELLM_BASE_URL", "http://litellm.litellm:4000")
    model_id = os.getenv("MODEL_ID", "qwen2-5-3b-neuron")
    logger.info("Model plane: %s (model_id=%s)", base_url, model_id)
    return OpenAIModel(
        client_args={
            "api_key": os.getenv("LITELLM_API_KEY", "sk-litellm"),
            "base_url": base_url,
        },
        model_id=model_id,
        params={"temperature": 0.2, "max_tokens": 1000},
    )


def build_tools() -> List[Any]:
    """Assemble tools according to which labs are 'switched on'."""
    tools: List[Any] = []

    # Order tools: local (lab 1) or over MCP (tool access lab)
    if os.getenv("ORDERS_TOOL_MODE", "local") == "mcp":
        from mcp.client.streamable_http import streamablehttp_client
        from strands.tools.mcp import MCPClient

        mcp_url = os.getenv("MCP_SERVER_URL", "http://shop-mcp.mcp-servers:8080/mcp")
        try:
            client = MCPClient(lambda: streamablehttp_client(mcp_url))
            client.start()
            mcp_tools = client.list_tools_sync()
            tools.extend(mcp_tools)
            logger.info("MCP tools from %s: %s", mcp_url, [t.tool_name for t in mcp_tools])
        except Exception as e:
            logger.error("MCP server unavailable (%s); falling back to local tool", e)
            from . import tools as local_tools
            tools.append(local_tools.lookup_order)
    else:
        from . import tools as local_tools
        tools.append(local_tools.lookup_order)

    # Product knowledge over Milvus RAG
    if os.getenv("MILVUS_URI"):
        from .rag import search_products
        tools.append(search_products)

    # Knowledge graph over Neo4j
    if os.getenv("NEO4J_URI"):
        from .kg import related_products
        tools.append(related_products)

    # Managed sandboxes (integrated track)
    if os.getenv("AGENTCORE_TOOLS") == "1":
        from .sandbox import browse_url, execute_python
        tools.extend([execute_python, browse_url])

    logger.info("Agent tools: %d loaded", len(tools))
    return tools


def build_agent(messages=None) -> Agent:
    return Agent(
        name="AnyCompany Shop Customer Agent",
        agent_id="customer_agent",
        description=(
            "Customer service agent for AnyCompany Shop: order status and "
            "tracking, product questions, inventory, and returns"
        ),
        model=build_model(),
        system_prompt=SYSTEM_PROMPT,
        tools=build_tools(),
        messages=messages,
    )


if __name__ == "__main__":
    agent = build_agent()
    print(agent("Where is my order ORD-12345?"))
