# Build from the repository root so the shared data files are in context:
#
#   docker buildx build --platform linux/amd64 \
#     -f app/mcp-server/Dockerfile -t shop-mcp:latest .

FROM python:3.12-slim

WORKDIR /app

COPY app/mcp-server/pyproject.toml app/mcp-server/README.md app/mcp-server/server.py ./
RUN pip install --no-cache-dir .

COPY data ./data

EXPOSE 8080

ENTRYPOINT ["shop-mcp"]
CMD ["--transport", "streamable-http"]
