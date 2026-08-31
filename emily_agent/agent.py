"""Emily: an autonomous coordination operator built on Google ADK + Gemini.

Emily drives a Meetless coordination Goal to completion. She reasons with Gemini
and acts through the Meetless MCP server (the public programmatic interface to the
coordination platform). She is a DRIVER, not a second planner: the Meetless kernel
plans the coordination; Emily launches it, supervises it, and proposes closure.

The MCP server is spawned as a stdio subprocess and Emily is given only the
operator-plane tools (submit / read / list / review / propose-close) plus
retrieve_knowledge for grounding.
"""

from __future__ import annotations

import os

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters

from .prompt import OPERATOR_INSTRUCTION

# The Gemini model. Default to the newest stable Flash that satisfies the
# hackathon's ">= 3.5" requirement; overridable so we can move to 3.7-flash.
MODEL = os.environ.get("EMILY_MODEL", "gemini-3.5-flash")

# The operator-plane tools Emily is allowed to see. The kernel's in-case planner
# verbs are intentionally NOT in the Meetless MCP surface at all, so this filter
# is a second, explicit guard that Emily only drives.
_ALLOWED_TOOLS = [
    "meetless__retrieve_knowledge",
    "meetless__coordination_submit_goal",
    "meetless__coordination_get_state",
    "meetless__coordination_list_proposals",
    "meetless__coordination_review_proposal",
    "meetless__coordination_propose_close",
]


def _mcp_env() -> dict[str, str]:
    """Environment for the spawned Meetless MCP server (headless shared-key path).

    Reads from Emily's own environment so the same process config flows through.
    """
    passthrough = [
        "MEETLESS_CONTROL_TOKEN",
        "MEETLESS_WORKSPACE_ID",
        "MEETLESS_BACKEND_URL",
        "MEETLESS_INTEL_URL",
        "MEETLESS_OPERATOR_USER_ID",
        "MEETLESS_NOTES_ROOT",
        # legacy alias accepted by the mcp bin
        "INTERNAL_API_KEY",
    ]
    env = {k: os.environ[k] for k in passthrough if os.environ.get(k)}
    # The mcp bin requires a workspace id and a control token; fail loudly early
    # rather than letting the subprocess exit(2) with a cryptic stdio close.
    if not env.get("MEETLESS_WORKSPACE_ID"):
        raise RuntimeError("MEETLESS_WORKSPACE_ID is required for the Meetless MCP server")
    if not (env.get("MEETLESS_CONTROL_TOKEN") or env.get("INTERNAL_API_KEY")):
        raise RuntimeError("MEETLESS_CONTROL_TOKEN (or INTERNAL_API_KEY) is required")
    return env


def _build_toolset() -> McpToolset:
    command = os.environ.get("MEETLESS_MCP_COMMAND", "node")
    # Default to the vendored self-contained bundle committed in this repo, so a
    # clean clone runs with no monorepo and no npm install. Override with
    # MEETLESS_MCP_SERVER to point at your own Meetless MCP build.
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    vendored = os.path.join(repo_root, "vendor", "meetless-mcp.mjs")
    default_server = os.environ.get("MEETLESS_MCP_SERVER", vendored)
    args_env = os.environ.get("MEETLESS_MCP_ARGS")
    args = args_env.split() if args_env else [default_server]
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=command,
                args=args,
                env=_mcp_env(),
            ),
            timeout=60.0,
        ),
        tool_filter=_ALLOWED_TOOLS,
    )


root_agent = LlmAgent(
    name="emily",
    model=MODEL,
    instruction=OPERATOR_INSTRUCTION,
    tools=[_build_toolset()],
)
