#!/usr/bin/env python3
"""Seed the data stores from the files in data/.

  --milvus   embed products + FAQs into the shop_products collection
  --neo4j    build the shop knowledge graph from orders + products

Run with port-forwards to the in-cluster services, or in-cluster as a Job.
  MILVUS_URI=http://localhost:19530 python scripts/seed_data.py --milvus
  NEO4J_URI=bolt://localhost:7687 NEO4J_PASSWORD=... python scripts/seed_data.py --neo4j
"""

import argparse
import json
import os
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
COLLECTION = os.getenv("MILVUS_PRODUCTS_COLLECTION", "shop_products")
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
DIM = 384

# Compatibility and bought-together edges for the knowledge graph
COMPATIBLE = [
    ("USB-C Hub", "Laptop Pro 15"),
    ("USB-C Hub", "Laptop Air 13"),
    ("Laptop Stand", "Laptop Pro 15"),
    ("Laptop Stand", "Laptop Air 13"),
    ("65W GaN Charger", "Laptop Pro 15"),
    ("65W GaN Charger", "Laptop Air 13"),
    ("Wireless Mouse", "USB-C Hub"),
]
BOUGHT_WITH = [
    ("Laptop Pro 15", "USB-C Hub"),
    ("Laptop Pro 15", "Noise Cancelling Headphones"),
    ("Laptop Air 13", "Wireless Mouse"),
    ("Wireless Mouse", "Mechanical Keyboard"),
    ("4K Monitor 27", "Laptop Stand"),
]


def load(name: str) -> dict:
    with open(DATA_DIR / name) as f:
        return json.load(f)


def seed_milvus():
    from pymilvus import MilvusClient
    from sentence_transformers import SentenceTransformer

    catalogue = load("products.json")
    entries = catalogue["products"] + catalogue["faqs"]
    texts = [f"{e['name']}. {e['description']}" for e in entries]

    print(f"Embedding {len(entries)} entries with {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)
    vectors = model.encode(texts, normalize_embeddings=True).tolist()

    client = MilvusClient(uri=os.getenv("MILVUS_URI", "http://localhost:19530"))
    if client.has_collection(COLLECTION):
        client.drop_collection(COLLECTION)
    client.create_collection(collection_name=COLLECTION, dimension=DIM, auto_id=True)

    rows = [
        {
            "vector": vector,
            "name": entry["name"],
            "category": entry["category"],
            "text": entry["description"],
        }
        for entry, vector in zip(entries, vectors)
    ]
    client.insert(collection_name=COLLECTION, data=rows)
    print(f"Seeded {len(rows)} rows into {COLLECTION}")


def seed_neo4j():
    from neo4j import GraphDatabase

    orders = load("orders.json")
    catalogue = load("products.json")

    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        for product in catalogue["products"]:
            session.run(
                "MERGE (p:Product {name: $name}) "
                "SET p.category = $category, p.price = $price",
                name=product["name"], category=product["category"], price=product["price"],
            )
        for order in orders.values():
            session.run(
                "MERGE (c:Customer {name: $customer}) "
                "MERGE (o:Order {id: $id}) SET o.status = $status, o.total = $total "
                "MERGE (c)-[:PLACED]->(o)",
                customer=order["customer"], id=order["order_id"],
                status=order["status"], total=order["total"],
            )
            for item in order["items"]:
                session.run(
                    "MATCH (o:Order {id: $id}) MERGE (p:Product {name: $product}) "
                    "MERGE (o)-[r:CONTAINS]->(p) SET r.quantity = $quantity",
                    id=order["order_id"], product=item["product"], quantity=item["quantity"],
                )
        for a, b in COMPATIBLE:
            session.run(
                "MATCH (a:Product {name: $a}), (b:Product {name: $b}) "
                "MERGE (a)-[:COMPATIBLE_WITH]->(b)", a=a, b=b,
            )
        for a, b in BOUGHT_WITH:
            session.run(
                "MATCH (a:Product {name: $a}), (b:Product {name: $b}) "
                "MERGE (a)-[:BOUGHT_WITH]->(b)", a=a, b=b,
            )
        count = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
    driver.close()
    print(f"Knowledge graph seeded: {count} nodes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--milvus", action="store_true")
    parser.add_argument("--neo4j", action="store_true")
    args = parser.parse_args()
    if not (args.milvus or args.neo4j):
        parser.error("pass --milvus and/or --neo4j")
    if args.milvus:
        seed_milvus()
    if args.neo4j:
        seed_neo4j()
