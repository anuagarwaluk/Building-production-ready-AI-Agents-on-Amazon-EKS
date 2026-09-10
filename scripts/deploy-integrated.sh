#!/usr/bin/env bash
# Deploy the integrated track: the same agent image against managed
# backends. Bedrock via LiteLLM (model_id change), AgentCore Memory,
# sandboxed tools, and dual-export tracing for AgentCore Evaluations.
set -euo pipefail

: "${ECR_REPO_CUSTOMER_AGENT_URI:?Run 'source scripts/env.sh' first}"
: "${AGENTCORE_MEMORY_ID:?Create an AgentCore Memory resource and export AGENTCORE_MEMORY_ID}"
export AWS_REGION
export LANGFUSE_PUBLIC_KEY="${LANGFUSE_PUBLIC_KEY:-}"
export LANGFUSE_SECRET_KEY="${LANGFUSE_SECRET_KEY:-}"

echo "==> customer agent (integrated backends)"
envsubst < deploy/k8s/customer-agent-integrated.yaml | kubectl apply -f -
kubectl -n agents rollout status deploy/customer-agent-integrated --timeout=300s || true

echo
echo "Integrated agent deployed. The diff that mattered:"
echo "  MODEL_ID=nova-lite  MEMORY_BACKEND=agentcore  AGENTCORE_TOOLS=1  AGENTCORE_OBSERVABILITY=1"
echo
echo "For multi-agent on managed backends, re-run the specialists with:"
echo "  MODEL_ID=nova-lite AGENTCORE_TOOLS=1 ./scripts/deploy-self-managed.sh"
echo
echo "Evaluation: evaluation/agentcore/create-evaluator.sh then run-evaluation.sh"
