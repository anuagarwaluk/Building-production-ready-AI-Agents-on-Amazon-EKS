################################################################################
# EKS Pod Identity: who is allowed to do what, with no static credentials
#
# Two identities, deliberately different:
#
#   litellm  -> Bedrock model invocation. Agents call models only through
#               the proxy, so ONLY the proxy holds model permissions.
#
#   agent    -> AgentCore data plane (memory, sandboxes, evaluations) and
#               trace export to AgentCore Observability. No Bedrock invoke:
#               an agent cannot bypass the model plane.
################################################################################

module "litellm_pod_identity" {
  source  = "terraform-aws-modules/eks-pod-identity/aws"
  version = "~> 2.0"

  name                 = "${local.name}-litellm-bedrock"
  attach_custom_policy = true
  policy_statements = [
    {
      sid = "BedrockInvoke"
      actions = [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ]
      resources = ["*"]
    }
  ]

  associations = {
    litellm = {
      cluster_name    = module.eks.cluster_name
      namespace       = var.litellm_namespace
      service_account = var.litellm_service_account
    }
  }

  tags = local.tags
}

module "agent_pod_identity" {
  source  = "terraform-aws-modules/eks-pod-identity/aws"
  version = "~> 2.0"

  name                 = "${local.name}-agent-agentcore"
  attach_custom_policy = true
  policy_statements = [
    {
      # Lab scope. For production, narrow to the specific memory, tool
      # session, and evaluation actions your agent uses.
      sid       = "AgentCoreDataPlane"
      actions   = ["bedrock-agentcore:*"]
      resources = ["*"]
    },
    {
      # Dual-export of OTel spans to the X-Ray OTLP endpoint
      sid = "TraceExport"
      actions = [
        "xray:PutTraceSegments",
        "xray:PutSpans",
        "xray:PutSpansForIndexing",
        "xray:PutTelemetryRecords"
      ]
      resources = ["*"]
    },
    {
      sid = "EvalLogs"
      actions = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:FilterLogEvents"
      ]
      resources = ["*"]
    }
  ]

  associations = {
    agent = {
      cluster_name    = module.eks.cluster_name
      namespace       = var.agent_namespace
      service_account = var.agent_service_account
    }
  }

  tags = local.tags
}

################################################################################
# Log group AgentCore Evaluations associates the agent's spans with.
# CloudWatch Transaction Search must also be enabled (account-level):
#   see docs/walkthrough-integrated.md
################################################################################

resource "aws_cloudwatch_log_group" "agentcore_eval" {
  name              = "/aws/bedrock-agentcore/runtimes/${var.agent_id}-eval"
  retention_in_days = 14

  tags = local.tags
}
