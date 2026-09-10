"""Tracing setup: Langfuse always, AgentCore Observability when asked.

Both tracks trace to Langfuse. The integrated evaluation module needs the
same spans in AgentCore Observability too (that is what AgentCore
Evaluations reads), so this module dual-exports: one global TracerProvider
feeds a SigV4 OTLP exporter to the X-Ray endpoint AND Langfuse's own
processor. The trace tree in Langfuse stays identical.

Three resource attributes make the evaluations service treat an EKS-hosted
agent like a first-class agent: the log group association, the
gen_ai_agent service type it filters on, and the resource id it parses the
agent id from. A Runtime-hosted agent gets these for free; on EKS we set
them explicitly.

Adapted from the workshop's evaluation module (30-integrated/550).
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "customer-agent")
AGENT_ID = os.getenv("AGENT_ID", "customer-agent")
REGION = os.getenv("AWS_REGION", "us-west-2")
AGENT_LOG_GROUP = os.getenv(
    "AGENTCORE_LOG_GROUP", f"/aws/bedrock-agentcore/runtimes/{AGENT_ID}-eval"
)


def init_tracing() -> Optional["object"]:
    """Configure the global TracerProvider. Returns the Langfuse client
    (or None when Langfuse is not configured). Call once at startup."""
    langfuse_enabled = bool(os.getenv("LANGFUSE_PUBLIC_KEY"))
    dual_export = os.getenv("AGENTCORE_OBSERVABILITY") == "1"

    if not langfuse_enabled and not dual_export:
        logger.info("Tracing disabled (no Langfuse keys, no dual export)")
        return None

    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    attributes = {"service.name": SERVICE_NAME}
    if dual_export:
        attributes.update({
            # Associates spans with the eval log group
            "aws.log.group.names": AGENT_LOG_GROUP,
            # The evaluations span query filters on this
            "aws.service.type": "gen_ai_agent",
            # Evaluations parses the agent id out of this
            "cloud.resource_id": f"runtime/{AGENT_ID}/eval",
        })

    provider = TracerProvider(resource=Resource.create(attributes))

    if dual_export:
        import boto3
        from amazon.opentelemetry.distro.exporter.otlp.aws.traces.otlp_aws_span_exporter import (
            OTLPAwsSpanExporter,
        )

        # The endpoint must be explicit; the exporter defaults to
        # localhost:4318 otherwise.
        aws_exporter = OTLPAwsSpanExporter(
            endpoint=f"https://xray.{REGION}.amazonaws.com/v1/traces",
            aws_region=REGION,
            session=boto3.Session(),
        )
        provider.add_span_processor(BatchSpanProcessor(aws_exporter))
        logger.info("Dual export enabled: X-Ray OTLP + Langfuse")

    trace.set_tracer_provider(provider)

    if langfuse_enabled:
        from langfuse import Langfuse

        # Langfuse v4 attaches its OWN processor to the SAME provider, so
        # spans reach both backends. Use the returned client.
        client = Langfuse(
            tracer_provider=provider,
            public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
            secret_key=os.environ["LANGFUSE_SECRET_KEY"],
            host=os.getenv("LANGFUSE_BASE_URL", "http://langfuse.langfuse:3000"),
        )
        logger.info("Langfuse tracing enabled (%s)", os.getenv("LANGFUSE_BASE_URL"))
        return client

    return None
