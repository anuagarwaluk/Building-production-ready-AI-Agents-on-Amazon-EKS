variable "name" {
  description = "Name prefix for the cluster and related resources"
  type        = string
  default     = "agents-on-eks"
}

variable "agent_namespace" {
  description = "Namespace the agents run in"
  type        = string
  default     = "agents"
}

variable "agent_service_account" {
  description = "Service account shared by the agent pods (Pod Identity association)"
  type        = string
  default     = "agent"
}

variable "litellm_namespace" {
  description = "Namespace for the LiteLLM proxy"
  type        = string
  default     = "litellm"
}

variable "litellm_service_account" {
  description = "Service account for the LiteLLM proxy (Bedrock access)"
  type        = string
  default     = "litellm"
}

variable "agent_id" {
  description = "Agent id used for the AgentCore Evaluations log group naming"
  type        = string
  default     = "customer-agent"
}
