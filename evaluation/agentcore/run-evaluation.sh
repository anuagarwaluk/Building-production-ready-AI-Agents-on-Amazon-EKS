#!/usr/bin/env bash
# Score one conversation with AgentCore Evaluations: two built-in
# evaluators plus the custom cs_accuracy evaluator.
#
# Prerequisites: the agent is running with AGENTCORE_OBSERVABILITY=1 (spans
# dual-exported to the X-Ray OTLP endpoint), CloudWatch Transaction Search
# is enabled for the account, and you have chatted with the agent so there
# is a session to score. Allow 60 to 90 seconds of indexing lag after
# chatting; spans land in the account-wide aws/spans log group.
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"

# 1. The session to score: most recent from the agent logs unless given
SESSION_ID="${SESSION_ID:-$(kubectl logs -n agents deployment/customer-agent --tail=100 \
  | grep -oE 'session=[^ ]+' | tail -1 | cut -d= -f2)}"
echo "Scoring session: ${SESSION_ID}"

# 2. The custom evaluator id (from create-evaluator.sh)
if [ -z "${CUSTOM_ID:-}" ]; then
  CUSTOM_ID=$(aws bedrock-agentcore-control list-evaluators --region "$AWS_REGION" \
    --query "evaluators[?evaluatorType=='Custom'].evaluatorId | [0]" --output text)
fi
echo "Using custom evaluator: ${CUSTOM_ID}"

# 3. Pull this session's spans out of aws/spans and shape them for evaluate
START=$(( ($(date +%s) - 3600) * 1000 ))
aws logs filter-log-events --region "$AWS_REGION" --log-group-name "aws/spans" \
  --start-time "$START" --max-items 300 --query 'events[].message' --output json \
  | jq --arg s "$SESSION_ID" \
      '{ sessionSpans: [ .[] | fromjson | select(.attributes."session.id" == $s) ] }' \
  > /tmp/eval_input.json

COUNT=$(jq '.sessionSpans | length' /tmp/eval_input.json)
echo "Spans collected: ${COUNT}"
if [ "$COUNT" = "0" ]; then
  echo "No spans yet. Wait 60 to 90 seconds after chatting and re-run." >&2
  exit 1
fi
TRACE_ID=$(jq -r '.sessionSpans[0].traceId' /tmp/eval_input.json)
echo "Trace: ${TRACE_ID}"

# 4. One evaluator per call, so loop over the three
for E in "Builtin.Correctness" "Builtin.Helpfulness" "$CUSTOM_ID"; do
  aws bedrock-agentcore evaluate --region "$AWS_REGION" \
    --evaluator-id "$E" \
    --evaluation-input  file:///tmp/eval_input.json \
    --evaluation-target "{\"traceIds\":[\"$TRACE_ID\"]}" \
    --query 'evaluationResults[0].{evaluator:evaluatorName,score:value,label:label,reason:explanation}' \
    --output json
done
