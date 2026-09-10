"""Orchestrator: routes customer requests to specialists over A2A.

The orchestrator holds no shop tools at all. It discovers the Order Agent
and Product Agent from their A2A cards and dispatches. The UI talks to it
through the same /chat contract as the single agent, so switching between
single-agent and multi-agent mode is a profile choice, not a UI change.
"""

import logging
import os
import sys
import uuid
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from strands import Agent
from strands_tools.a2a_client import A2AClientToolProvider

from ..agent import build_model
from ..telemetry import init_tracing

logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") == "1" else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
logger = logging.getLogger(__name__)

LANGFUSE = init_tracing()

app = FastAPI(title="AnyCompany Shop Orchestrator", version="1.0.0")


def specialist_urls() -> list[str]:
    return [
        os.getenv("ORDER_AGENT_URL", "http://order-agent.agents:9000"),
        os.getenv("PRODUCT_AGENT_URL", "http://product-agent.agents:9000"),
    ]


def build_orchestrator() -> Agent:
    provider = A2AClientToolProvider(known_agent_urls=specialist_urls())
    tools = provider.tools
    logger.info("Discovered A2A tools: %s", [t.tool_name for t in tools])
    return Agent(
        name="AnyCompany Shop Orchestrator",
        agent_id="orchestrator_agent",
        description="Routes AnyCompany Shop customer requests to specialist agents",
        model=build_model(),
        system_prompt="""
        You are the front-of-house agent for AnyCompany Shop. Discover the
        available specialist agents and route each request:
        - Orders, tracking, inventory, returns: the order specialist
        - Product questions, recommendations, policies, computation: the
          product specialist
        Combine specialist answers into one clear reply. If a request needs
        both specialists, call both.
        """,
        tools=tools,
    )


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")
    session_id = request.session_id or f"session-{uuid.uuid4()}"
    try:
        from opentelemetry import trace

        tracer = trace.get_tracer("orchestrator-agent")
        with tracer.start_as_current_span("chat") as span:
            span.set_attribute("session.id", session_id)
            reply = str(build_orchestrator()(request.message.strip()))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Orchestrator failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    return ChatResponse(reply=reply, session_id=session_id)


def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    logger.info("Orchestrator listening on %s:%s", host, port)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
