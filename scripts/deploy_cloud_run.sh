#!/usr/bin/env bash
# Deploy Emily to Cloud Run.
#
# Requires a deploy-capable identity (interactive: `gcloud auth login` as a project
# owner/editor, or a deploy service account). The session read-only SA cannot deploy.
#
# The Meetless backend Emily drives already runs on Cloud Run in prod-meetless
# (meetless-control / meetless-intel / meetless-worker), so the "backend on Google
# Cloud" requirement is met by that project regardless of where this agent runs.
#
# Secrets (create once in Secret Manager, never commit):
#   GOOGLE_API_KEY          Gemini API key
#   MEETLESS_CONTROL_TOKEN  workspace INTERNAL_API_KEY for the target backend
#   MEETLESS_WORKSPACE_ID   the demo workspace id
set -euo pipefail

PROJECT="${PROJECT:-prod-meetless}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-emily-agent}"
BACKEND_URL="${MEETLESS_BACKEND_URL:-https://meetless-control-653554733822.us-central1.run.app}"
INTEL_URL="${MEETLESS_INTEL_URL:-https://meetless-intel-653554733822.us-central1.run.app}"

gcloud run deploy "$SERVICE" \
  --source . \
  --project "$PROJECT" \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "EMILY_MODEL=gemini-3.5-flash,GOOGLE_GENAI_USE_VERTEXAI=FALSE,MEETLESS_BACKEND_URL=${BACKEND_URL},MEETLESS_INTEL_URL=${INTEL_URL},MEETLESS_MCP_COMMAND=node,MEETLESS_MCP_SERVER=/app/vendor/meetless-mcp.mjs" \
  --set-secrets "GOOGLE_API_KEY=GOOGLE_API_KEY:latest,MEETLESS_CONTROL_TOKEN=MEETLESS_CONTROL_TOKEN:latest,MEETLESS_WORKSPACE_ID=MEETLESS_WORKSPACE_ID:latest"

echo "Deployed. Service URL:"
gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format='value(status.url)'
