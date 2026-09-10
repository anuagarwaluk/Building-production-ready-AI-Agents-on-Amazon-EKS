"""Knowledge graph tool over Neo4j.

Vector search finds things that sound similar. It cannot walk
relationships: which hub fits which laptop, what people buy together,
which order contained which product. The final self-managed lab adds a
small graph for exactly those questions.

scripts/seed_data.py builds the graph:
  (Customer)-[:PLACED]->(Order)-[:CONTAINS]->(Product)
  (Product)-[:COMPATIBLE_WITH]->(Product)
  (Product)-[:BOUGHT_WITH]->(Product)
"""

import logging
import os
from functools import lru_cache

from strands import tool

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _driver():
    from neo4j import GraphDatabase

    uri = os.getenv("NEO4J_URI", "bolt://neo4j.neo4j:7687")
    auth = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
    logger.info("Connecting to Neo4j at %s", uri)
    return GraphDatabase.driver(uri, auth=auth)


@tool
def related_products(product_name: str) -> str:
    """Find products related to a given product through the knowledge graph:
    compatible accessories and items frequently bought together.

    Use when a customer asks what works with a product, what to add to an
    order, or for recommendations tied to something specific.

    Args:
        product_name: Exact or partial product name, e.g. "Laptop Pro 15"
    """
    query = """
    MATCH (p:Product) WHERE toLower(p.name) CONTAINS toLower($name)
    OPTIONAL MATCH (p)-[:COMPATIBLE_WITH]-(c:Product)
    OPTIONAL MATCH (p)-[:BOUGHT_WITH]-(b:Product)
    RETURN p.name AS product,
           collect(DISTINCT c.name) AS compatible,
           collect(DISTINCT b.name) AS bought_together
    LIMIT 3
    """
    try:
        with _driver().session() as session:
            records = list(session.run(query, name=product_name))
    except Exception as e:
        logger.error("Neo4j query failed: %s", e)
        return f"Knowledge graph is unavailable right now: {e}"

    if not records:
        return f"No product matching '{product_name}' in the knowledge graph."

    lines = []
    for record in records:
        compatible = ", ".join(x for x in record["compatible"] if x) or "none recorded"
        bought = ", ".join(x for x in record["bought_together"] if x) or "none recorded"
        lines.append(
            f"{record['product']}\n  Compatible with: {compatible}\n  Frequently bought with: {bought}"
        )
    return "\n".join(lines)
