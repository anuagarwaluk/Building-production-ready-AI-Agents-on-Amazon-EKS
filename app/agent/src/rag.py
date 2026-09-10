"""Product knowledge via RAG on Milvus.

The catalogue (13 products plus store FAQs) is embedded into a Milvus
collection by scripts/seed_data.py. At question time the agent embeds the
query, runs a vector search, and answers from what comes back. Vector
search answers "what is similar"; for "what is related" see kg.py.
"""

import logging
import os
from functools import lru_cache

from strands import tool

logger = logging.getLogger(__name__)

COLLECTION = os.getenv("MILVUS_PRODUCTS_COLLECTION", "shop_products")
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


@lru_cache(maxsize=1)
def _client():
    from pymilvus import MilvusClient

    uri = os.getenv("MILVUS_URI", "http://milvus.milvus:19530")
    logger.info("Connecting to Milvus at %s", uri)
    return MilvusClient(uri=uri)


@lru_cache(maxsize=1)
def _embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL)


def embed(texts: list[str]) -> list[list[float]]:
    return _embedder().encode(texts, normalize_embeddings=True).tolist()


@tool
def search_products(query: str) -> str:
    """Search the AnyCompany Shop product catalogue and store FAQs.

    Use for product questions (features, prices, compatibility) and store
    policy questions (returns, shipping, warranty, payment).

    Args:
        query: The customer's question or a short search phrase
    """
    try:
        results = _client().search(
            collection_name=COLLECTION,
            data=embed([query]),
            limit=4,
            output_fields=["name", "category", "text"],
        )
    except Exception as e:
        logger.error("Milvus search failed: %s", e)
        return f"Product search is unavailable right now: {e}"

    hits = results[0] if results else []
    if not hits:
        return "No matching products or FAQs found."

    lines = []
    for hit in hits:
        entity = hit.get("entity", {})
        lines.append(
            f"[{entity.get('category', '?')}] {entity.get('name', '?')}: "
            f"{entity.get('text', '')} (score {hit.get('distance', 0):.3f})"
        )
    return "\n".join(lines)
