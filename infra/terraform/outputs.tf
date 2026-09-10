output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "configure_kubectl" {
  description = "Command to update kubeconfig"
  value       = "aws eks update-kubeconfig --region ${data.aws_region.current.id} --name ${module.eks.cluster_name}"
}

output "ecr_repo_customer_agent" {
  description = "ECR repository for the customer agent image"
  value       = aws_ecr_repository.customer_agent.repository_url
}

output "ecr_repo_shop_mcp" {
  description = "ECR repository for the shop MCP server image"
  value       = aws_ecr_repository.shop_mcp.repository_url
}

output "ecr_repo_chat_ui" {
  description = "ECR repository for the chat UI image"
  value       = aws_ecr_repository.chat_ui.repository_url
}

output "agentcore_eval_log_group" {
  description = "Log group AgentCore Evaluations reads the agent's spans from"
  value       = aws_cloudwatch_log_group.agentcore_eval.name
}
