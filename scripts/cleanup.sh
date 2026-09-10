#!/usr/bin/env bash
# Tear everything down. Workloads first (releases load balancers, lets
# Auto Mode scale nodes to zero, removes the Inferentia node), then Helm
# releases, then the infrastructure.
set -euo pipefail

echo "==> Application workloads"
kubectl delete -f deploy/k8s/ --ignore-not-found 2>/dev/null || true

echo "==> Platform workloads"
kubectl delete -f platform/vllm/qwen25-3b-neuron.yaml --ignore-not-found 2>/dev/null || true
kubectl delete -f platform/vllm/nodepool-inferentia.yaml --ignore-not-found 2>/dev/null || true
kubectl delete -f platform/litellm/deployment.yaml --ignore-not-found 2>/dev/null || true
helm uninstall langfuse -n langfuse 2>/dev/null || true
helm uninstall milvus -n milvus 2>/dev/null || true
helm uninstall neo4j -n neo4j 2>/dev/null || true
kubectl delete namespace agents mcp-servers litellm vllm ui langfuse milvus neo4j --ignore-not-found 2>/dev/null || true

echo "==> AgentCore resources (delete any you created)"
echo "    aws bedrock-agentcore-control list-agent-runtimes"
echo "    aws bedrock-agentcore-control list-evaluators --query \"evaluators[?evaluatorType=='Custom']\""
echo "    (delete custom evaluators and any Memory resources you created)"

echo "==> Infrastructure"
terraform -chdir="$(dirname "$0")/../infra/terraform" destroy -auto-approve

echo "Cleanup complete. Verify in the console: EKS, EC2 (no inf2 nodes, no"
echo "load balancers, no NAT leftovers), ECR, CloudWatch log groups."
