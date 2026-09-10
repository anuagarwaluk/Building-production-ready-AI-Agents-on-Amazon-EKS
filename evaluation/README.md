# Evaluation: the same question, answered two ways

A trace tells you what the agent did. It does not tell you whether the answer was any good. Both tracks close that gap with LLM-as-a-Judge, but the machinery differs, and comparing the two was one of the most instructive parts of the build.

| | Self-managed (`langfuse_judge.py`) | Integrated (`agentcore/`) |
|---|---|---|
| Judge | Claude Sonnet 4.5 via LiteLLM, driven by my script | AgentCore Evaluations, a managed Bedrock service |
| Trace source | Langfuse | AgentCore Observability (spans dual-exported to X-Ray) |
| Evaluators | Custom rubric in a prompt | Built-in Correctness and Helpfulness, plus a custom `cs_accuracy` evaluator |
| Levels | Trace | Span, trace, or session |
| Runs from | Anywhere with Langfuse access | `bedrock-agentcore` CLI |

## The dimensions scored

| Dimension | Question it answers | Why it matters for a shop |
|---|---|---|
| Correctness | Are the facts in the reply consistent with the tool results? | Hallucinated order status or prices erode customer trust |
| Helpfulness | Does the reply resolve the request clearly? | A correct but vague reply still creates a follow-up contact |
| cs_accuracy (custom) | Did the agent ground its answer in a real `lookup_order` result rather than inventing details? | The retail-specific check the built-ins cannot express |

## The finding worth remembering

The managed judge scored the integrated agent higher on accuracy than the self-managed one. Not because the agent was smarter. The integrated agent's traces carried tool-call spans tagged with `session.id`, so the judge could verify grounding directly; the earlier traces lacked tool spans, so grounding could not be proven and scored near zero. Same judge methodology, richer traces, higher scores. What you can measure depends on what you emit.

## Running the integrated evaluation

```bash
export AWS_REGION=us-west-2
./agentcore/create-evaluator.sh       # once
./agentcore/run-evaluation.sh         # per conversation
```

Both scripts are CLI-only; no code changes to the agent beyond the dual-export telemetry already in `app/agent/src/telemetry.py`. Note that enabling CloudWatch Transaction Search is an account-level setting: it routes X-Ray segments to CloudWatch Logs for the whole account and region, which matters in a shared account.
