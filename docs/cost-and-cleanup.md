# Cost notes and cleanup

Approximate lab-scale figures at public list prices as of September 2026. Check current pricing before relying on any number; the shape matters more than the pennies.

## What costs money while this runs

| Component | Driver | Behaviour |
|---|---|---|
| EKS control plane | Flat hourly fee | Always on while the cluster exists (about $0.10/hour) |
| General purpose nodes | EC2 while workloads run | Auto Mode scales to zero when workloads are removed |
| Inferentia (inf2) node | EC2 while the vLLM deployment exists | The big line item of the self-managed track; delete the deployment when idle and the pool scales to zero |
| NAT gateway | Hourly plus data | Always on (about $0.045/hour) |
| Bedrock (Nova Lite, judge model) | Per token | Zero when idle; Nova Lite is priced for exactly this kind of high-volume, small-task work |
| AgentCore (Memory, sandboxes, Evaluations) | Consumption | Zero when idle |
| Milvus, Neo4j, Langfuse | The nodes and volumes they occupy | Persistent volumes keep billing until the Helm releases and PVCs are deleted |

Two behaviours define the economics:

1. **The self-managed track's cost is capacity-shaped.** The Inferentia node bills while it exists, whether or not anyone chats. Its unit economics win at sustained scale and lose at lab scale.
2. **The integrated track's cost is usage-shaped.** Bedrock and AgentCore bill per use and idle at zero. A pilot waiting for traffic costs almost nothing.

That contrast is not a lab artefact; it is the honest summary of the strategy decision. Parking the self-managed track overnight without deleting the vLLM deployment is the expensive mistake to avoid.

## Cleanup

```bash
./scripts/cleanup.sh
```

Order matters: application workloads, then the vLLM deployment and NodePool (releases the inf2 node), then Helm releases and their PVCs, then any AgentCore runtimes, evaluators, and memory resources you created (the script prints the list commands), then `terraform destroy`. Verify in the console afterwards: EKS gone, no inf2 instances, no load balancers, no orphaned volumes, CloudWatch log groups you no longer want removed. If you enabled CloudWatch Transaction Search for a shared account, decide deliberately whether to leave it on; it is account-level.
