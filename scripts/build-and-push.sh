#!/usr/bin/env bash
# Build and push the three application images to ECR. Run from the
# repository root after 'source scripts/env.sh'. Images are built for
# linux/amd64 to match the cluster's general-purpose nodes.
set -euo pipefail

: "${AWS_REGION:?Run 'source scripts/env.sh' first}"
: "${ECR_REPO_CUSTOMER_AGENT_URI:?Run 'source scripts/env.sh' first}"

REGISTRY="${ECR_REPO_CUSTOMER_AGENT_URI%%/*}"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$REGISTRY"

echo "==> customer-agent (root context: data files baked in)"
docker buildx build --platform linux/amd64 --push \
  -f app/agent/Dockerfile \
  -t "${ECR_REPO_CUSTOMER_AGENT_URI}:latest" \
  .

echo "==> shop-mcp"
docker buildx build --platform linux/amd64 --push \
  -f app/mcp-server/Dockerfile \
  -t "${ECR_REPO_SHOP_MCP_URI}:latest" \
  .

echo "==> chat-ui"
docker buildx build --platform linux/amd64 --push \
  -t "${ECR_REPO_CHAT_UI_URI}:latest" \
  app/ui

echo "All images pushed."
