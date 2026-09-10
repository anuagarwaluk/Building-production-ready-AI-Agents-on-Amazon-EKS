"""Chainlit chat UI for AnyCompany Shop.

Four chat profiles, one per combination of track and mode. Every profile
speaks the same /chat contract; the only difference is which in-cluster
Service it targets. That is the workshop's design and it is worth copying:
the UI never learns which infrastructure answered.
"""

import os
import uuid

import chainlit as cl
import httpx

PROFILES = {
    "Customer Agent (Self-Managed GenAI)": {
        "url": os.getenv("SELF_MANAGED_AGENT_URL", "http://customer-agent.agents:8000"),
        "description": "Single agent. Qwen2.5-3B on Inferentia via vLLM and LiteLLM.",
    },
    "Customer Agent (Integrated GenAI)": {
        "url": os.getenv("INTEGRATED_AGENT_URL", "http://customer-agent-integrated.agents:8000"),
        "description": "Single agent. Amazon Bedrock via LiteLLM, AgentCore Memory and sandboxes.",
    },
    "Multi-Agent (Self-Managed GenAI)": {
        "url": os.getenv("SELF_MANAGED_ORCHESTRATOR_URL", "http://orchestrator.agents:8000"),
        "description": "Orchestrator routing to Order and Product specialists over A2A.",
    },
    "Multi-Agent (Integrated GenAI)": {
        "url": os.getenv("INTEGRATED_ORCHESTRATOR_URL", "http://orchestrator-integrated.agents:8000"),
        "description": "A2A specialists on the integrated backends.",
    },
}


@cl.set_chat_profiles
async def chat_profiles():
    return [
        cl.ChatProfile(name=name, markdown_description=profile["description"])
        for name, profile in PROFILES.items()
    ]


@cl.on_chat_start
async def start():
    cl.user_session.set("session_id", f"session-{uuid.uuid4()}")
    profile = cl.user_session.get("chat_profile") or next(iter(PROFILES))
    await cl.Message(
        content=(
            f"Welcome to AnyCompany Shop support ({profile}).\n\n"
            "Try: `Where is my order ORD-12345?` or "
            "`Which hub works with the Laptop Air 13?`"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    profile = cl.user_session.get("chat_profile") or next(iter(PROFILES))
    target = PROFILES[profile]["url"].rstrip("/")
    session_id = cl.user_session.get("session_id")

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{target}/chat",
                json={"message": message.content, "session_id": session_id},
            )
            response.raise_for_status()
            reply = response.json().get("reply", "(empty reply)")
    except Exception as e:
        reply = f"The agent behind this profile is not reachable: {e}"

    await cl.Message(content=reply).send()
