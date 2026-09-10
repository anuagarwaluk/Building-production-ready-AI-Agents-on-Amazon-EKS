#!/usr/bin/env bash
# Deploy the shared platform: namespaces, the LiteLLM model plane, and the
# self-managed model serving. Stateful services (Langfuse, Milvus, Neo4j)
# install from their official Helm charts; see platform/<name>/README.md.
set -euo pipefail

: "${AWS_REGION:?Run 'source scripts/env.sh' first}"

kubectl apply -f platform/namespaces.yaml

echo "==> LiteLLM (the shared model plane)"
kubectl apply -f platform/litellm/configmap.yaml
export AWS_REGION
envsubst < platform/litellm/deployment.yaml | kubectl apply -f -
kubectl -n litellm rollout status deploy/litellm --timeout=300s

echo "==> Inferentia node pool + vLLM (self-managed inference)"
kubectl apply -f platform/vllm/nodepool-inferentia.yaml
if [ -n "${VLLM_NEURON_IMAGE:-}" ]; then
  envsubst < platform/vllm/qwen25-3b-neuron.yaml | kubectl apply -f -
  echo "vLLM deploying; first start takes several minutes (node + model + compile)."
else
  echo "VLLM_NEURON_IMAGE not set; skipping vLLM. Set it and re-run, or use the"
  echo "integrated track (Bedrock via LiteLLM) which needs no self-hosted model."
fi

echo
echo "Next: install Langfuse, Milvus, and Neo4j per platform/*/README.md,"
echo "seed data with scripts/seed_data.py, then deploy the agents."
