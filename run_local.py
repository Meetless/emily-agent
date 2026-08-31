"""Drive Emily locally with the ADK Runner and print her reasoning + tool calls.

Usage:
    python run_local.py "objective text" [--goal-id GID] [--turns "msg1" "msg2" ...]

Sends one or more operator messages to Emily in a single session and streams every
tool call, tool result, and text response so you can watch Gemini plan and drive
the real Meetless coordination.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from google.adk.runners import InMemoryRunner
from google.genai import types

from emily_agent.agent import root_agent

APP = "emily"
USER = "operator"


def _fmt(obj, n=500):
    try:
        return json.dumps(obj, default=str)[:n]
    except Exception:
        return str(obj)[:n]


async def _send(runner, session_id, text):
    print(f"\n\033[1m>>> OPERATOR:\033[0m {text}\n")
    content = types.Content(role="user", parts=[types.Part(text=text)])
    async for event in runner.run_async(user_id=USER, session_id=session_id, new_message=content):
        for part in (event.content.parts if event.content else []) or []:
            if getattr(part, "function_call", None):
                fc = part.function_call
                print(f"  \033[36m[tool call]\033[0m {fc.name}({_fmt(dict(fc.args or {}), 300)})")
            elif getattr(part, "function_response", None):
                fr = part.function_response
                print(f"  \033[35m[tool result]\033[0m {fr.name} -> {_fmt(fr.response, 400)}")
            elif getattr(part, "text", None):
                if part.text.strip():
                    print(f"  \033[32m[emily]\033[0m {part.text.strip()}")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("objective")
    ap.add_argument("--turns", nargs="*", default=[])
    args = ap.parse_args()

    runner = InMemoryRunner(agent=root_agent, app_name=APP)
    session = await runner.session_service.create_session(app_name=APP, user_id=USER)
    try:
        await _send(runner, session.id, args.objective)
        for t in args.turns:
            await _send(runner, session.id, t)
    finally:
        # Close the MCP toolset subprocess cleanly.
        for tool in root_agent.tools:
            close = getattr(tool, "close", None)
            if close:
                try:
                    await close()
                except Exception:
                    pass


if __name__ == "__main__":
    asyncio.run(main())
