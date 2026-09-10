# Walkthrough: self-managed track

Everything on EKS. No managed AI services; pods, Helm charts, and Python. The agent gains one capability per stage, matching the workshop's nine labs, and each stage keeps everything from the ones before.

## 0. Infrastructure

```bash
cd infra/terraform && terraform init && terraform apply
source scripts/env.sh
./scripts/build-and-push.sh
./scripts/deploy-platform.sh
```

Terraform builds the VPC, EKS Auto Mode cluster (Kubernetes 1.34), ECR repos, Pod Identity roles, and the evaluations log group. The platform script deploys LiteLLM, the Inferentia NodePool, and (with `VLLM_NEURON_IMAGE` set) vLLM serving Qwen2.5-3B. Install Langfuse, Milvus, and Neo4j from their official charts per `platform/*/README.md`.

## 1. Model plane: vLLM + LiteLLM

The single most consequential design decision in the repo. Agents call `http://litellm.litellm:4000` with the OpenAI API; LiteLLM routes `qwen2-5-3b-neuron` to the vLLM service on the Inferentia node. Verify before any agent exists:

```bash
kubectl -n litellm port-forward svc/litellm 4000:4000 &
curl -s localhost:4000/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model": "qwen2-5-3b-neuron", "messages": [{"role": "user", "content": "One sentence: what is EKS?"}]}'
```

## 2. The agent

`app/agent/src/agent.py` builds a Strands agent with `OpenAIModel` pointed at the plane. Lab 1 configuration is the smallest possible: `ORDERS_TOOL_MODE=local`, one tool (`lookup_order`), three hardcoded orders. Deploy and ask it where ORD-12345 is; the model decides to call the tool, the tool returns the order, the agent answers grounded.

## 3. Observability with Langfuse

Set the `LANGFUSE_*` env vars on the deployment and every LLM call, tool invocation, and decision lands in Langfuse as OpenTelemetry spans. This lab comes third on purpose: everything after it gets debugged from traces.

## 4. RAG with Milvus

```bash
kubectl -n milvus port-forward svc/milvus 19530:19530 &
MILVUS_URI=http://localhost:19530 python scripts/seed_data.py --milvus
```

Thirteen products and four store FAQs become vectors in `shop_products`. With `MILVUS_URI` set, the agent gains `search_products` and starts answering "does the USB-C Hub work with the Laptop Air 13?" from the catalogue instead of the model's imagination.

## 5. Memory with Milvus

`MEMORY_BACKEND=milvus` turns on semantic memory: every turn is embedded, and recall is a vector search filtered to the session. Ask about an order, then ask "has it shipped yet?" and watch the recalled context arrive in the trace.

## 6. Tool access over MCP

`ORDERS_TOOL_MODE=mcp` retires the hardcoded tool. The shop MCP server (`deploy/k8s/mcp-server.yaml`) now owns `lookup_order`, `check_inventory`, and `process_return`, and any agent, or any MCP client anywhere, can use them. Tools became a service.

## 7. Multi-agent with A2A

```bash
./scripts/deploy-self-managed.sh
```

The generalist splits: an Order Agent (transactions) and a Product Agent (knowledge), each publishing an A2A Agent Card, plus an Orchestrator that discovers them and routes. The UI's multi-agent profile hits the orchestrator's `/chat`; the reply weaves both specialists' answers.

## 8. Evaluation with LLM-as-a-Judge

```bash
python evaluation/langfuse_judge.py --limit 10
```

Claude Sonnet 4.5 (via the same LiteLLM plane) reads recent traces and scores retail accuracy: did the agent ground its claims in tool results? Scores attach to the traces in Langfuse. Note what this lab exposes: conversations whose traces lack tool spans cannot prove grounding and score near zero. Remember that for the integrated evaluation lab.

## 9. Knowledge graph with Neo4j

```bash
NEO4J_URI=bolt://localhost:7687 NEO4J_PASSWORD=... python scripts/seed_data.py --neo4j
```

Set `NEO4J_URI` on the agent and it gains `related_products`, answering relationship questions vector search cannot: compatibility, bought-together, customer purchase paths. RAG and the graph coexist; the agent picks per question.

## What this track proves

You can run a complete agentic stack, model included, on infrastructure you fully control, with open weights, portable components, and total debuggability. The cost is that every one of those layers is now yours to patch, scale, and keep alive. The integrated track (`walkthrough-integrated.md`) is the counter-argument, and the same agent code runs in both.
