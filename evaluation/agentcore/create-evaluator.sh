#!/usr/bin/env bash
# Create the custom cs_accuracy evaluator in Amazon Bedrock AgentCore
# Evaluations. The two built-ins (Builtin.Correctness, Builtin.Helpfulness)
# ship with the service; only the custom retail evaluator needs creating.
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
CONFIG="$(dirname "$0")/cs_accuracy_config.json"

echo "Built-in evaluators available:"
aws bedrock-agentcore-control list-evaluators --region "$AWS_REGION" \
  --query "evaluators[?evaluatorType=='Builtin'].evaluatorId" --output text

CUSTOM_ID=$(aws bedrock-agentcore-control create-evaluator \
  --region "$AWS_REGION" \
  --evaluator-name cs_accuracy \
  --level TRACE \
  --description "Retail order-accuracy evaluator (tool-grounded)" \
  --evaluator-config "file://${CONFIG}" \
  --query 'evaluatorId' --output text)

echo "Created custom evaluator: ${CUSTOM_ID}"
echo "Export it for the run script:  export CUSTOM_ID=${CUSTOM_ID}"
