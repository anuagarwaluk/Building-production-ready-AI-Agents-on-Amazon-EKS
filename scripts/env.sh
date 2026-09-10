#!/usr/bin/env bash
# Export environment from Terraform outputs. Source after 'terraform apply':
#   source scripts/env.sh
set -a

AWS_REGION="${AWS_REGION:-$(aws configure get region)}"
TF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../infra/terraform" && pwd)"

CLUSTER_NAME="$(terraform -chdir="$TF_DIR" output -raw cluster_name)"
ECR_REPO_CUSTOMER_AGENT_URI="$(terraform -chdir="$TF_DIR" output -raw ecr_repo_customer_agent)"
ECR_REPO_SHOP_MCP_URI="$(terraform -chdir="$TF_DIR" output -raw ecr_repo_shop_mcp)"
ECR_REPO_CHAT_UI_URI="$(terraform -chdir="$TF_DIR" output -raw ecr_repo_chat_ui)"
AGENTCORE_LOG_GROUP="$(terraform -chdir="$TF_DIR" output -raw agentcore_eval_log_group)"

set +a

echo "Cluster:      $CLUSTER_NAME ($AWS_REGION)"
echo "Agent image:  $ECR_REPO_CUSTOMER_AGENT_URI"
echo "MCP image:    $ECR_REPO_SHOP_MCP_URI"
echo "UI image:     $ECR_REPO_CHAT_UI_URI"

aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME" >/dev/null
echo "kubeconfig updated."
