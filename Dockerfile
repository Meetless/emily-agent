# Emily on Cloud Run: a Python ADK/Gemini agent that also runs the Meetless MCP
# server (Node) as a stdio subprocess, so the image carries both runtimes.
FROM python:3.11-slim

# Node.js for the Meetless MCP server.
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# The Meetless MCP server. By default we install the published package; for a
# build that includes coordination tools not yet on npm, drop a self-contained
# bundle at vendor/meetless-mcp.mjs and set MEETLESS_MCP_SERVER to it.
COPY emily_agent ./emily_agent
COPY vendor ./vendor

ENV MEETLESS_MCP_COMMAND=node \
    MEETLESS_MCP_SERVER=/app/vendor/meetless-mcp.mjs \
    GOOGLE_GENAI_USE_VERTEXAI=FALSE \
    EMILY_MODEL=gemini-3.5-flash \
    PORT=8080

# Serve the agent over HTTP via the ADK API server. The workspace + token +
# backend URLs are provided at deploy time (env + Secret Manager).
CMD exec adk api_server --host 0.0.0.0 --port ${PORT} /app
