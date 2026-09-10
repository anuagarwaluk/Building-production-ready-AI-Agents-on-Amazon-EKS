#!/usr/bin/env bash
# Smoke-test the deployed agents through port-forwards.
set -euo pipefail

cleanup() { jobs -p | xargs -r kill 2>/dev/null || true; }
trap cleanup EXIT

ask() {
  local port=$1 message=$2
  curl -sf -X POST "http://localhost:${port}/chat" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"${message}\", \"session_id\": \"smoke-test\"}" | head -c 700
  echo; echo
}

echo "==> Single agent"
kubectl -n agents port-forward svc/customer-agent 8000:8000 >/dev/null 2>&1 &
sleep 3
curl -sf http://localhost:8000/health && echo
ask 8000 "Where is my order ORD-12345?"
ask 8000 "Is the Noise Cancelling Headphones in stock?"

echo "==> Multi-agent orchestrator"
kubectl -n agents port-forward svc/orchestrator 8001:8000 >/dev/null 2>&1 &
sleep 3
ask 8001 "I ordered ORD-67890. What did it cost in total, and what would you recommend to go with it?"

echo "==> A2A agent card (order specialist)"
kubectl -n agents port-forward svc/order-agent 9000:9000 >/dev/null 2>&1 &
sleep 3
curl -sf http://localhost:9000/.well-known/agent-card.json | head -c 400
echo; echo "Done."
