"""Self-managed evaluation: LLM-as-a-Judge inside Langfuse.

Pulls recent traces from Langfuse, asks a judge model (via the same
LiteLLM proxy the agents use) to score each conversation for retail
accuracy, and writes the scores back onto the traces so they show up in
the Langfuse UI next to the conversations they grade.

This is the self-managed counterpart to evaluation/agentcore, where the
judging is a managed Bedrock service instead.

Run from anywhere with network access to Langfuse and LiteLLM:
  LANGFUSE_PUBLIC_KEY=... LANGFUSE_SECRET_KEY=... LANGFUSE_BASE_URL=... \
  LITELLM_BASE_URL=... python evaluation/langfuse_judge.py --limit 10
"""

import argparse
import json
import os

import httpx
from langfuse import Langfuse

JUDGE_MODEL = os.getenv("JUDGE_MODEL_ID", "claude-sonnet-4-5")

RUBRIC = """You are a senior customer-service QA auditor for an online
retailer. Evaluate the ACCURACY of this agent interaction.

Conversation input: {input}
Agent response: {output}

Did the agent ground its answer in tool results rather than inventing
order details, prices, or stock levels? Score:
  1.0 fully grounded, no invented details
  0.5 mostly grounded, minor unsupported detail
  0.0 invented details or ignored tool results

Reply with JSON only: {{"score": <number>, "reason": "<one sentence>"}}"""


def judge(input_text: str, output_text: str) -> dict:
    base_url = os.getenv("LITELLM_BASE_URL", "http://localhost:4000").rstrip("/")
    response = httpx.post(
        f"{base_url}/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('LITELLM_API_KEY', 'sk-litellm')}"},
        json={
            "model": JUDGE_MODEL,
            "messages": [{
                "role": "user",
                "content": RUBRIC.format(input=input_text[:6000], output=output_text[:6000]),
            }],
            "temperature": 0,
        },
        timeout=120,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    start, end = content.find("{"), content.rfind("}") + 1
    return json.loads(content[start:end])


def main():
    parser = argparse.ArgumentParser(description="Score recent traces with LLM-as-a-Judge")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--score-name", default="cs_accuracy")
    args = parser.parse_args()

    langfuse = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.getenv("LANGFUSE_BASE_URL", "http://localhost:3000"),
    )

    traces = langfuse.api.trace.list(limit=args.limit).data
    print(f"Scoring {len(traces)} traces with {JUDGE_MODEL}")

    for trace in traces:
        input_text = json.dumps(trace.input, default=str) if trace.input else ""
        output_text = json.dumps(trace.output, default=str) if trace.output else ""
        if not output_text:
            continue
        try:
            verdict = judge(input_text, output_text)
        except Exception as e:
            print(f"  {trace.id}: judge failed ({e})")
            continue
        langfuse.create_score(
            trace_id=trace.id,
            name=args.score_name,
            value=float(verdict.get("score", 0)),
            comment=verdict.get("reason", ""),
        )
        print(f"  {trace.id}: {verdict.get('score')} ({verdict.get('reason', '')[:80]})")

    langfuse.flush()
    print("Done. Scores are on the traces in the Langfuse UI.")


if __name__ == "__main__":
    main()
