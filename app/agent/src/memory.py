"""Conversation memory, two ways.

Self-managed: past turns are embedded into Milvus and recalled by semantic
search. "What did this customer ask before that is relevant now?"

Integrated: turns become events in Amazon Bedrock AgentCore Memory, and
recall returns the recent conversation. The service handles storage,
retention, and (with managed strategies) extraction.

server.py picks the backend from MEMORY_BACKEND: none | milvus | agentcore.
The agent code does not know which one is in play, which is the point.
"""

import logging
import os
import time
import uuid
from functools import lru_cache
from typing import List, Tuple

logger = logging.getLogger(__name__)


class NoMemory:
    def store(self, session_id: str, role: str, text: str) -> None:
        pass

    def recall(self, session_id: str, query: str) -> str:
        return ""


class MilvusMemory:
    """Semantic memory: embed every turn, recall the most relevant ones."""

    COLLECTION = os.getenv("MILVUS_MEMORY_COLLECTION", "conversation_memory")
    DIM = 384  # all-MiniLM-L6-v2

    def __init__(self):
        from pymilvus import MilvusClient

        self.client = MilvusClient(uri=os.getenv("MILVUS_URI", "http://milvus.milvus:19530"))
        if not self.client.has_collection(self.COLLECTION):
            self.client.create_collection(
                collection_name=self.COLLECTION,
                dimension=self.DIM,
                auto_id=False,
                primary_field_name="id",
                id_type="string",
                vector_field_name="vector",
                max_length=64,
            )

    def _embed(self, text: str) -> list:
        from .rag import embed

        return embed([text])[0]

    def store(self, session_id: str, role: str, text: str) -> None:
        try:
            self.client.insert(
                collection_name=self.COLLECTION,
                data=[{
                    "id": str(uuid.uuid4()),
                    "vector": self._embed(text),
                    "session_id": session_id,
                    "role": role,
                    "text": text[:4000],
                    "ts": int(time.time()),
                }],
            )
        except Exception as e:
            logger.error("Memory store failed: %s", e)

    def recall(self, session_id: str, query: str) -> str:
        try:
            results = self.client.search(
                collection_name=self.COLLECTION,
                data=[self._embed(query)],
                limit=4,
                filter=f'session_id == "{session_id}"',
                output_fields=["role", "text"],
            )
        except Exception as e:
            logger.error("Memory recall failed: %s", e)
            return ""
        hits = results[0] if results else []
        turns = [f"{h['entity']['role']}: {h['entity']['text']}" for h in hits]
        return "\n".join(reversed(turns))


class AgentCoreMemory:
    """Session memory in Amazon Bedrock AgentCore Memory.

    Requires an existing memory resource (AGENTCORE_MEMORY_ID) and IAM
    permissions on the pod via EKS Pod Identity. Uses the bedrock-agentcore
    SDK's MemoryClient: create_event to record turns, get_last_k_turns to
    recall the recent conversation.
    """

    def __init__(self):
        from bedrock_agentcore.memory import MemoryClient

        self.memory_id = os.environ["AGENTCORE_MEMORY_ID"]
        self.client = MemoryClient(region_name=os.getenv("AWS_REGION", "us-west-2"))

    def store(self, session_id: str, role: str, text: str) -> None:
        try:
            self.client.create_event(
                memory_id=self.memory_id,
                actor_id=session_id,
                session_id=session_id,
                messages=[(text[:8000], "USER" if role == "user" else "ASSISTANT")],
            )
        except Exception as e:
            logger.error("AgentCore Memory store failed: %s", e)

    def recall(self, session_id: str, query: str) -> str:
        try:
            turns: List[List[Tuple]] = self.client.get_last_k_turns(
                memory_id=self.memory_id,
                actor_id=session_id,
                session_id=session_id,
                k=4,
            )
        except Exception as e:
            logger.error("AgentCore Memory recall failed: %s", e)
            return ""
        lines = []
        for turn in turns or []:
            for message in turn:
                role = message.get("role", "?") if isinstance(message, dict) else str(message[1])
                content = (
                    message.get("content", {}).get("text", "")
                    if isinstance(message, dict)
                    else str(message[0])
                )
                lines.append(f"{role}: {content}")
        return "\n".join(lines)


@lru_cache(maxsize=1)
def get_memory():
    backend = os.getenv("MEMORY_BACKEND", "none").lower()
    logger.info("Memory backend: %s", backend)
    if backend == "milvus":
        return MilvusMemory()
    if backend == "agentcore":
        return AgentCoreMemory()
    return NoMemory()
