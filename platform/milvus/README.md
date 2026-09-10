# Vector database: Milvus

Milvus carries two jobs in the self-managed track:

1. **Product RAG**: the 13 product descriptions and store FAQs are embedded into the `shop_products` collection. The agent's `search_products` tool answers catalogue and policy questions from it.
2. **Semantic memory**: every conversation turn is embedded into `conversation_memory`. Recall is a vector search filtered by session, so the agent surfaces the *relevant* past turns, not just the recent ones.

## Install (official Helm chart, standalone mode)

```bash
helm repo add milvus https://zilliztech.github.io/milvus-helm/
helm repo update
kubectl create namespace milvus
helm install milvus milvus/milvus -n milvus \
  --set cluster.enabled=false \
  --set etcd.replicaCount=1 \
  --set minio.mode=standalone \
  --set pulsarv3.enabled=false
kubectl -n milvus rollout status deploy/milvus-standalone --timeout=600s
```

## Seed the catalogue

```bash
MILVUS_URI=http://localhost:19530 python scripts/seed_data.py --milvus
# (port-forward first: kubectl -n milvus port-forward svc/milvus 19530:19530)
```

Embeddings use `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions) by default; change `EMBED_MODEL` consistently in the seeder and the agent or the vectors will not match.
