# Knowledge graph: Neo4j

The final self-managed lab. Vector search answers "what is similar"; it cannot walk relationships. The graph answers what RAG cannot:

- Which accessories are compatible with the Laptop Air 13?
- What do customers who bought the Laptop Pro 15 also buy?
- Which order contained which product, for which customer?

Model:

```
(Customer)-[:PLACED]->(Order)-[:CONTAINS]->(Product)
(Product)-[:COMPATIBLE_WITH]->(Product)
(Product)-[:BOUGHT_WITH]->(Product)
```

## Install (official Helm chart)

```bash
helm repo add neo4j https://helm.neo4j.com/neo4j
helm repo update
kubectl create namespace neo4j
helm install neo4j neo4j/neo4j -n neo4j \
  --set neo4j.name=shop-graph \
  --set neo4j.password=<choose-a-password> \
  --set volumes.data.mode=defaultStorageClass
kubectl -n neo4j rollout status statefulset/neo4j --timeout=600s
```

## Seed the graph

```bash
NEO4J_URI=bolt://localhost:7687 NEO4J_PASSWORD=<password> \
  python scripts/seed_data.py --neo4j
# (port-forward first: kubectl -n neo4j port-forward svc/neo4j 7687:7687)
```

Then set `NEO4J_URI` and `NEO4J_PASSWORD` on the agent deployment to switch the `related_products` tool on.
