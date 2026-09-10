"""Shared A2A server plumbing.

Each specialist publishes an Agent Card at /.well-known/agent-card.json and
answers A2A messages on port 9000 at the root path, with /ping for probes.
This is also the AgentCore Runtime service contract for A2A agents, so a
specialist built this way can later move onto the managed runtime
unchanged (the runtime injects AGENTCORE_RUNTIME_URL for the card).
"""

import logging
import os

import uvicorn
from fastapi import FastAPI
from strands import Agent
from strands.multiagent.a2a import A2AServer

logger = logging.getLogger(__name__)


def serve_a2a(agent: Agent) -> None:
    host = os.getenv("A2A_HOST", "0.0.0.0")
    port = int(os.getenv("A2A_PORT", "9000"))
    http_url = os.getenv(
        "A2A_URL", os.getenv("AGENTCORE_RUNTIME_URL", f"http://localhost:{port}")
    )

    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"status": "healthy"}

    server = A2AServer(
        agent=agent, host=host, port=port, http_url=http_url, serve_at_root=True
    )
    app.mount("/", server.to_fastapi_app())

    logger.info("Agent Card: http://localhost:%s/.well-known/agent-card.json", port)
    logger.info("Advertised A2A URL: %s", http_url)
    uvicorn.run(app, host=host, port=port)
