#!/usr/bin/env bash
# Deploy the self-managed track: MCP server, customer agent (Qwen via
# LiteLLM, Milvus RAG + memory, Neo4j, Langfuse), A2A specialists, and UI.
# Run from the repository root after env.sh, build-and-push.sh, and the
# platform installs.
set -euo pipefail

: "${ECR_REPO_CUSTOMER_AGENT_URI:?Run 'source scripts/env.sh' first}"
export MODEL_ID="${MODEL_ID:-qwen2-5-3b-neuron}"
export AGENTCORE_TOOLS="${AGENTCORE_TOOLS:-0}"
export LANGFUSE_PUBLIC_KEY="${LANGFUSE_PUBLIC_KEY:-}"
export LANGFUSE_SECRET_KEY="${LANGFUSE_SECRET_KEY:-}"
export NEO4J_PASSWORD="${NEO4J_PASSWORD:-}"

echo "==> shop MCP server"
envsubst < deploy/k8s/mcp-server.yaml | kubectl apply -f -

echo "==> customer agent (self-managed backends)"
envsubst < deploy/k8s/customer-agent-selfmanaged.yaml | kubectl apply -f -

echo "==> A2A specialists + orchestrator"
envsubst < deploy/k8s/a2a-specialists.yaml | kubectl apply -f -

echo "==> chat UI"
envsubst < deploy/k8s/ui.yaml | kubectl apply -f -

kubectl -n mcp-servers rollout status deploy/shop-mcp --timeout=180s || true
kubectl -n agents rollout status deploy/customer-agent --timeout=300s || true
kubectl -n agents rollout status deploy/orchestrator --timeout=300s || true
kubectl -n ui rollout status deploy/chat-ui --timeout=180s || true

echo
echo "Deployed. Chat:  kubectl -n ui port-forward svc/chat-ui 8080:8080"
echo "Or smoke test:   ./scripts/test-chat.sh"
