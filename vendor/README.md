# Vendored Meetless MCP server

`meetless-mcp.mjs` is a self-contained (bundled + minified) build of the Meetless MCP
server. Emily spawns it as a stdio subprocess to reach the Meetless coordination
platform over the Model Context Protocol. It is vendored here so this repository is
independently runnable without a Meetless monorepo checkout or an npm install.

## What it exposes

The read/evidence tools (`retrieve_knowledge`, `kb_doc_detail`, `query`, ...) plus the
five coordination DRIVER tools Emily uses:
`coordination_submit_goal`, `coordination_get_state`, `coordination_list_proposals`,
`coordination_review_proposal`, `coordination_propose_close`. It intentionally does
NOT expose the kernel's in-case planner verbs (require/capture/verify/transition).

## Provenance

- Source: `meetless-cli/packages/mcp/` in the private Meetless monorepo.
- The coordination DRIVER tools were added during the hackathon submission period
  (they wrap pre-existing Meetless control endpoints; no new backend behavior).
- Everything the bundle talks to (the Meetless control/worker/intel coordination
  kernel) is pre-existing Meetless work, disclosed as an integrated dependency.

## No secrets

The bundle contains no credentials, workspace ids, or hostnames. All of those come
from environment variables at runtime (`MEETLESS_WORKSPACE_ID`,
`MEETLESS_CONTROL_TOKEN`, `MEETLESS_BACKEND_URL`, `MEETLESS_INTEL_URL`).

## Rebuild / replace

From a Meetless monorepo checkout:

```bash
cd meetless-cli/packages/mcp
npx esbuild server.js --bundle --minify --platform=node --format=esm \
  --outfile=/path/to/emily-agent/vendor/meetless-mcp.mjs
```

Or point `MEETLESS_MCP_SERVER` at your own Meetless MCP build (or `npx @meetless/mcp`
once the coordination tools are published there). Requires Node.js at runtime.
