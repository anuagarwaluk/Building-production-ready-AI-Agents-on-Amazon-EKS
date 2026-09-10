# Build from the repository root so the shared data files are in context:
#
#   docker buildx build --platform linux/amd64 \
#     -f app/agent/Dockerfile -t customer-agent:latest .
#
# One image serves four roles via its entrypoints:
#   customer-agent (default), orchestrator-agent, order-agent, product-agent

FROM python:3.12-slim AS build

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY app/agent/pyproject.toml app/agent/README.md ./
COPY app/agent/src ./src
# Include the integrated-track extras so the same image runs both tracks
RUN uv venv && uv pip install --no-cache ".[agentcore]"

FROM python:3.12-slim

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    HF_HOME=/tmp/hf

COPY --from=build /app/.venv .venv
COPY data ./data

EXPOSE 8000 9000

ENTRYPOINT ["customer-agent"]
