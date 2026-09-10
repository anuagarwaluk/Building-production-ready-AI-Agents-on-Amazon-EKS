"""The /chat endpoint every UI profile talks to.

POST /chat {"message": "...", "session_id": "..."} -> {"reply": "..."}

Per request: recall relevant memory for the session, run the agent with
that context, store the new turns, and tag the trace with session.id so
evaluation tooling can find the conversation later.
"""

import logging
import os
import sys
import uuid
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") == "1" else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
logger = logging.getLogger(__name__)

from .agent import build_agent
from .memory import get_memory
from .telemetry import init_tracing

# One provider for the process; Strands emits spans through it
LANGFUSE = init_tracing()

app = FastAPI(title="AnyCompany Shop Customer Agent", version="1.0.0")


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
    message = request.message.strip()
    logger.info("chat session=%s message=%s", session_id, message[:200])

    memory = get_memory()
    context = memory.recall(session_id, message)
    prompt = (
        f"Relevant context from this customer's earlier conversation:\n{context}\n\n"
        f"Customer: {message}"
        if context
        else message
    )

    try:
        from opentelemetry import trace

        tracer = trace.get_tracer("customer-agent")
        with tracer.start_as_current_span("chat") as span:
            # session.id is how AgentCore Evaluations groups a conversation
            span.set_attribute("session.id", session_id)
            span.set_attribute("gen_ai.conversation.id", session_id)
            agent = build_agent()
            reply = str(agent(prompt))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Agent failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e) if os.getenv("DEBUG") else "Internal server error",
        )

    memory.store(session_id, "user", message)
    memory.store(session_id, "assistant", reply)

    if LANGFUSE is not None:
        try:
            LANGFUSE.flush()
        except Exception:
            pass

    return ChatResponse(reply=reply, session_id=session_id)


def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    logger.info("Customer agent listening on %s:%s", host, port)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
