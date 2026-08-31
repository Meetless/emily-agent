"""End-to-end demo: Emily drives a real Meetless coordination Goal to CLOSED.

This is a DEV/DEMO harness (not part of the shipped agent). It requires a local
Meetless checkout because it (a) provisions a fresh billed workspace and (b)
simulates the human authoritative replies that, in production, real owners send in
Slack. Emily herself is the standalone ADK agent in emily_agent/.

Flow:
  1. Provision a fresh workspace (CheckoutRunner).
  2. Emily (Gemini) grounds and submits the Goal.
  3. The Meetless kernel decomposes it into Conditions and queues outreach.
  4. Emily supervises: she approves the on-objective proposals.
  5. The accountable humans reply authoritatively (simulated here).
  6. The kernel captures the decisions, verifies the Conditions -> SATISFIED.
  7. Emily proposes closure; the server's structural gate closes the Goal.

Run (from emily-agent/, venv active, control+worker+intel up):
    python scripts/demo.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time

# --- wire in the local Meetless monorepo helpers (provisioning + human replies) ---
_HERE = os.path.dirname(os.path.abspath(__file__))
_EMILY_ROOT = os.path.dirname(_HERE)  # <projects>/meetless/emily-agent
_PROJECTS_MEETLESS = os.path.dirname(_EMILY_ROOT)  # <projects>/meetless
_MONOREPO = os.path.join(_PROJECTS_MEETLESS, "meetless")
_CONTROL_ENV = os.path.join(_MONOREPO, "apps", "control", ".env")
sys.path.insert(0, _EMILY_ROOT)  # so `import emily_agent` resolves
sys.path.insert(0, os.path.join(_MONOREPO, "tools", "scenarios", "agent"))


def _read_env_file(path):
    out = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k] = v.strip().strip('"').strip("\r")
    return out


def _c(color, text):
    return f"\033[{color}m{text}\033[0m"


async def _run_turn(runner, session_id, text, capture_goal=False):
    from google.genai import types

    print("\n" + _c("1", f">>> OPERATOR: {text}"))
    content = types.Content(role="user", parts=[types.Part(text=text)])
    goal_id = None
    async for event in runner.run_async(user_id="operator", session_id=session_id, new_message=content):
        for part in (event.content.parts if event.content else []) or []:
            if getattr(part, "function_call", None):
                fc = part.function_call
                print(_c("36", f"  [tool] {fc.name}({json.dumps(dict(fc.args or {}), default=str)[:160]})"))
            elif getattr(part, "function_response", None):
                fr = part.function_response
                blob = json.dumps(fr.response, default=str)
                if capture_goal and "goalCaseId" in blob:
                    try:
                        inner = json.loads(fr.response["content"][0]["text"])
                        goal_id = inner.get("goalCaseId") or goal_id
                    except Exception:
                        pass
                print(_c("35", f"  [result] {fr.name} -> {blob[:200]}"))
            elif getattr(part, "text", None) and part.text.strip():
                print(_c("32", f"  [emily] {part.text.strip()}"))
    return goal_id


def _decision_for(ask_text: str) -> str:
    t = (ask_text or "").lower()
    if "rate" in t or "limit" in t:
        return "Approved: cap push notifications at 5 per user per hour, with a burst of 10; drop the rest."
    if "opt-out" in t or "retention" in t or "data" in t:
        return "Approved: purge opt-out records 30 days after the user opts out; no marketing retention."
    if "retry" in t or "payment" in t:
        return "Approved: exponential backoff, max 3 retries, then fail closed and alert."
    if "timeout" in t or "budget" in t or "provider" in t:
        return "Approved: 800ms per-attempt provider timeout budget."
    return "Approved: proceed as proposed for the Tuesday release."


async def main():
    cenv = _read_env_file(_CONTROL_ENV)
    os.environ.setdefault("MEETLESS_BACKEND_URL", "http://127.0.0.1:3006")
    os.environ.setdefault("MEETLESS_INTEL_URL", "http://127.0.0.1:8100")
    os.environ["INTERNAL_API_KEY"] = cenv["INTERNAL_API_KEY"]
    os.environ["MEETLESS_CONTROL_TOKEN"] = cenv["INTERNAL_API_KEY"]
    os.environ["DATABASE_URL"] = cenv["DATABASE_URL"]
    if not os.environ.get("GOOGLE_API_KEY"):
        ienv = _read_env_file(os.path.join(_PROJECTS_MEETLESS, "intel", ".env"))
        os.environ["GOOGLE_API_KEY"] = ienv.get("GOOGLE_API_KEY", "")
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")

    from lib.checkout_runner import CheckoutRunner
    from lib.product_reply_driver import ProductReplyDriver
    from lib.reactive_actors import EmilyAsk

    runner_ml = CheckoutRunner()
    print(_c("1", "\n=== Provisioning a fresh demo workspace ==="))
    ctx = runner_ml.provision()
    print(f"workspace={ctx.workspace_id} owner={ctx.owner_user_id}")

    # Emily drives THIS workspace. Set env before importing the agent (it builds
    # its MCP toolset at import from these vars).
    os.environ["MEETLESS_WORKSPACE_ID"] = ctx.workspace_id
    os.environ["MEETLESS_OPERATOR_USER_ID"] = ctx.owner_user_id

    from google.adk.runners import InMemoryRunner
    from emily_agent.agent import root_agent

    arunner = InMemoryRunner(agent=root_agent, app_name="emily")
    session = await arunner.session_service.create_session(app_name="emily", user_id="operator")

    # DEMO-WORKSPACE BOOTSTRAP ONLY. The kernel routes each ask to the ownership
    # owner (retry -> tl_checkout, timeout -> qa_checkout), and that owner must be
    # SEATED as a stakeholder or DriveService.createOutboundMessage throws
    # "stakeholder not found". For this preconfigured demo we seat the whole team so
    # whichever routed owner the kernel picks is present. This is NOT the production
    # authority model: routing ownership and decision authority are different
    # concepts, and production seats owners deliberately, not en masse. The
    # submit_goal tool itself seats only the decision_owners it is given.
    team = [ctx.owner_user_id] + list(ctx.persona_user.values())
    team_list = ", ".join(team)

    objective = (
        "Get the Checkout pilot ready for the Monday beta. Two things are still open: "
        "the payment retry policy and the provider timeout budget. "
        f"Seat this whole team as the decision owners so the kernel can route each decision to its "
        f"accountable owner: {team_list}."
    )

    reply = ProductReplyDriver(
        base_url=os.environ["MEETLESS_BACKEND_URL"],
        internal_key=os.environ["INTERNAL_API_KEY"],
        approver_user_id=ctx.owner_user_id,
        persona_slack_ids=ctx.persona_slack,
    )
    answered = set()
    final = None

    def _cond_status(gid):
        dto = runner_ml.read_goal(ctx)
        conds = (dto or {}).get("goal", {}).get("conditions", [])
        return (dto or {}).get("goal", {}).get("status"), [
            (c.get("conditionId"), c.get("conditionStatus")) for c in conds
        ]

    def _deliver_replies():
        # The accountable humans reply authoritatively (simulated in this harness;
        # in production they reply in Slack).
        for a in runner_ml.observe_asks(ctx):
            if a.ask_id in answered:
                continue
            text = _decision_for(a.text)
            print(_c("33", f"[human:{a.persona}] -> {text}"))
            reply.deliver_reply(persona=a.persona, text=text, in_reply_to=EmilyAsk(a.persona, a.text, a.ask_id))
            answered.add(a.ask_id)

    try:
        # Turn 1: Emily grounds + submits the goal.
        goal_id = await _run_turn(
            arunner, session.id,
            f"{objective}\n\nLaunch the coordination now and report the goal id.",
            capture_goal=True,
        )
        ctx.goal_id = goal_id
        print(_c("1", f"\n[harness] goal_id = {goal_id}"))

        # SUPERVISE LOOP. The kernel decomposes sequentially and asks/replies are
        # async, so we interleave: each pass Emily approves any pending proposals
        # and proposes closure if ready; the harness delivers any human replies.
        deadline = time.time() + 600
        passno = 0
        while time.time() < deadline:
            passno += 1
            status, conds = _cond_status(goal_id)
            props = runner_ml.observe_proposals(ctx)
            asks = runner_ml.observe_asks(ctx)
            print(_c("1", f"\n[harness pass {passno}] goal={status} conditions={conds} "
                          f"pendingProposals={len(props)} pendingAsks={len(asks)} answered={len(answered)}"))
            if status == "CLOSED":
                final = "CLOSED"
                break

            # Emily supervises: approve queued proposals, and propose close if ready.
            await _run_turn(
                arunner, session.id,
                f"Check the state of goal {goal_id}. Approve every pending proposal that advances the "
                "objective. If coordination_get_state shows every condition SATISFIED, propose closing "
                "the goal and report exactly what the server ruled. Otherwise report who we are waiting "
                "on. Keep it brief.",
            )

            # Humans respond to whatever asks have dispatched.
            _deliver_replies()

            status, _ = _cond_status(goal_id)
            if status == "CLOSED":
                final = "CLOSED"
                break
            time.sleep(8)

        if final != "CLOSED":
            final, _ = _cond_status(goal_id)
        print(_c("1", f"\n=== FINAL: goal status = {final} ==="))
        if final == "CLOSED":
            print(_c("32", "PASS: Emily drove the goal to CLOSED end to end."))
            code = 0
        else:
            print(_c("31", f"FAIL: goal did not close (status={final})."))
            code = 1
    finally:
        for tool in root_agent.tools:
            close = getattr(tool, "close", None)
            if close:
                try:
                    await close()
                except Exception:
                    pass
        if os.environ.get("EMILY_KEEP") != "1":
            runner_ml.teardown(ctx.workspace_id)

    sys.exit(code)


if __name__ == "__main__":
    asyncio.run(main())
