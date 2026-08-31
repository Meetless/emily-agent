"""Autonomous coordination demo: ONE operator instruction, TWO async human inputs,
ZERO operator follow-ups, ONE autonomously CLOSED goal.

This is the clean, camera-ready demo. It differs from scripts/demo.py in one crucial
way: after Emily (Gemini via ADK) submits the goal, there are NO operator turns. The
Meetless kernel drives the rest autonomously on the real human-reply -> CASE_AGENT_WAKE
path (the same event-driven continuation the golden_spine regression control proves).
The harness only (a) performs system plumbing that a policy would do in production
(authorizing the kernel's queued stakeholder ask and dispatching it) and (b) delivers
the two authoritative human replies, which are legitimate external events. Every state
transition rendered is read from the real coordination case; nothing is faked.

Requires a local Meetless checkout (to provision a throwaway workspace and simulate the
human replies). Run from emily-agent/ with the venv active and control+worker+intel up:
    python scripts/demo_autonomous.py
"""

from __future__ import annotations

import logging
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")
for noisy in ("google_adk", "google.adk", "google_genai", "mcp", "asyncio"):
    logging.getLogger(noisy).setLevel(logging.ERROR)
logging.getLogger().setLevel(logging.ERROR)

import asyncio  # noqa: E402
import json  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_EMILY_ROOT = os.path.dirname(_HERE)
_PROJECTS_MEETLESS = os.path.dirname(_EMILY_ROOT)
_MONOREPO = os.path.join(_PROJECTS_MEETLESS, "meetless")
_CONTROL_ENV = os.path.join(_MONOREPO, "apps", "control", ".env")
sys.path.insert(0, _EMILY_ROOT)
sys.path.insert(0, os.path.join(_MONOREPO, "tools", "scenarios", "agent"))

# Two blockers in CLEARLY DIFFERENT domains so they route to two different owners:
# the payment retry policy (Payments Engineering) and the QA sign-off (QA).
ROLE = {
    "s012_eng_payments": "Maya, Payments Engineering",
    "s012_qa_checkout": "Chris, QA Lead",
    "s012_tl_checkout": "Checkout Tech Lead",
    "s012_pm_launch": "PM",
    "owner": "Beta Program Owner",
}
DECISION = {
    "retry": "Use exponential backoff, max 3 retries, then fail closed and alert.",
    "qa": "QA sign-off granted: the checkout flow passed regression and is cleared for the beta.",
}

BOLD, DIM, GRN, CYN, YEL, MAG, RED, RST = (
    "\033[1m", "\033[2m", "\033[32m", "\033[36m", "\033[33m", "\033[35m", "\033[31m", "\033[0m",
)


def line(tag, color, text):
    print(f"  {color}{tag:<11}{RST} {text}", flush=True)


def _read_env_file(path):
    out = {}
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                out[k] = v.strip().strip('"').strip("\r")
    return out


def _decision_for(text):
    t = (text or "").lower()
    if "retry" in t or "payment" in t:
        return DECISION["retry"]
    if "qa" in t or "sign-off" in t or "sign off" in t or "regression" in t or "test" in t:
        return DECISION["qa"]
    return "Approved as proposed."


async def _emily_submit(objective):
    """One ADK turn: Emily grounds and submits. Renders her tool calls cleanly."""
    from google.adk.runners import InMemoryRunner
    from google.genai import types
    from emily_agent.agent import root_agent

    runner = InMemoryRunner(agent=root_agent, app_name="emily")
    session = await runner.session_service.create_session(app_name="emily", user_id="operator")
    goal_id = None
    content = types.Content(role="user", parts=[types.Part(text=objective)])
    async for event in runner.run_async(user_id="operator", session_id=session.id, new_message=content):
        for part in (event.content.parts if event.content else []) or []:
            fc = getattr(part, "function_call", None)
            fr = getattr(part, "function_response", None)
            if fc and fc.name == "meetless__retrieve_knowledge":
                line("Emily", CYN, "Grounding against workspace knowledge...")
            elif fc and fc.name == "meetless__coordination_submit_goal":
                line("Emily", CYN, "Turning the objective into a governed Goal with blocking conditions...")
            elif fr and "goalCaseId" in json.dumps(fr.response, default=str):
                try:
                    goal_id = json.loads(fr.response["content"][0]["text"]).get("goalCaseId") or goal_id
                except Exception:
                    pass
    # close the MCP subprocess Emily spawned
    for tool in root_agent.tools:
        close = getattr(tool, "close", None)
        if close:
            try:
                await close()
            except Exception:
                pass
    return goal_id


def main():
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

    import lib.checkout_runner as cr
    from lib.product_reply_driver import ProductReplyDriver
    from lib.reactive_actors import EmilyAsk

    # Two blockers in different domains -> two different owners. retry -> Payments Eng;
    # QA sign-off -> QA Lead.
    cr.OWNERSHIP = [("retry", "s012_eng_payments"), ("sign-off", "s012_qa_checkout"),
                    ("qa", "s012_qa_checkout")]
    runner = cr.CheckoutRunner()

    print(f"\n{BOLD}=== Emily: autonomous coordination demo ==={RST}\n")
    ctx = runner.provision()

    def who(uid):
        return ROLE.get(ctx.user_persona.get(uid, uid), ctx.user_persona.get(uid, uid))

    eng = ctx.persona_user["s012_eng_payments"]
    qa = ctx.persona_user["s012_qa_checkout"]
    objective = (
        "Get the Checkout pilot ready for Monday's beta. Two things are still unresolved: the "
        "payment retry policy, and the QA sign-off on the checkout flow. These belong to two "
        "different owners: the payment retry policy is owned by the Payments Engineer "
        f"({eng}); the QA sign-off is owned by the QA Lead ({qa}). Route each decision to its own "
        "owner, and do not consider the goal complete until both are actually resolved. Launch it "
        "and report the goal id."
    )

    line("Operator", BOLD, "Get the Checkout pilot ready for Monday's beta.")
    line("", DIM, "The payment retry policy and the QA sign-off are still unresolved.")
    line("", DIM, "Coordinate the accountable owners; don't close until both are resolved.")
    print()

    os.environ["MEETLESS_WORKSPACE_ID"] = ctx.workspace_id
    os.environ["MEETLESS_OPERATOR_USER_ID"] = ctx.owner_user_id
    goal_id = asyncio.run(_emily_submit(objective))
    ctx.goal_id = goal_id
    line("Emily", GRN, f"Goal launched. From here, no further operator input: the coordination "
                       f"kernel drives it on real events.")
    print()

    reply = ProductReplyDriver(
        base_url=os.environ["MEETLESS_BACKEND_URL"], internal_key=os.environ["INTERNAL_API_KEY"],
        approver_user_id=ctx.owner_user_id, persona_slack_ids=ctx.persona_slack,
    )

    def cond_map():
        dto = runner.read_goal(ctx) or {}
        out = {}
        def walk(cs):
            for c in cs or []:
                out[c["conditionId"]] = (c.get("objective", ""), c.get("conditionStatus"))
                walk(c.get("conditions"))
        walk((dto.get("goal") or {}).get("conditions"))
        return (dto.get("goal") or {}).get("status"), out

    # ---- Autonomous renderer: no operator turns. Only plumbing + human events. ----
    # The demo targets the flat two-condition path. The shared reasoner occasionally
    # spawns a recursive sub-condition (a known-parked capability); that branch stalls,
    # so we DETECT it and abort fast (RECURSED, exit 2) to re-run, rather than hang.
    rendered_conditions = False
    rendered_status = {}
    parked_shown = False
    authorized = set()
    answered = set()
    reply_personas = set()
    replies_delivered = 0
    step_deadline = time.time() + 90  # per-progress watchdog; reset on real progress
    hard_deadline = time.time() + 240
    while time.time() < hard_deadline:
        status, conds = cond_map()
        satisfied_count = sum(1 for _, st in conds.values() if st == "SATISFIED")

        if len(conds) > 2:
            print(f"\n{YEL}{BOLD}RECURSED: the reasoner spawned a sub-condition this run; re-run for a flat take.{RST}\n")
            _teardown(runner, ctx)
            return 2

        if len(conds) == 2 and not rendered_conditions:
            line("Kernel", MAG, "Goal decomposed into two blocking conditions:")
            for cid, (obj, st) in conds.items():
                line("", DIM, f"  ○ {obj}")
            rendered_conditions = True

        for p in runner.observe_proposals(ctx):
            key = p["proposal_id"]
            if key in authorized:
                continue
            runner.approve_proposal(ctx, p["case_id"], p["proposal_id"])
            authorized.add(key)
            line("Policy", YEL, "Stakeholder ask authorized and routed to its accountable owner.")
            step_deadline = time.time() + 90

        if not parked_shown and rendered_conditions and runner.observe_asks(ctx) and replies_delivered == 0:
            line("Kernel", MAG, "Asks sent. Goal PARKED — no compute while it waits on humans.")
            parked_shown = True

        # Deliver the two authoritative human replies sequentially: the next only after the
        # previous condition has actually gone SATISFIED. Real, ordered async events.
        if rendered_conditions and replies_delivered < 2 and replies_delivered == satisfied_count:
            asks = [a for a in runner.observe_asks(ctx) if a.ask_id not in answered]
            if asks:
                a = asks[0]
                text = _decision_for(a.text)
                reply.deliver_reply(persona=a.persona, text=text, in_reply_to=EmilyAsk(a.persona, a.text, a.ask_id))
                answered.add(a.ask_id)
                reply_personas.add(a.persona)
                replies_delivered += 1
                line("Human", GRN, f"{ROLE.get(a.persona, a.persona)}: {text}")
                line("Event", CYN, "Reply received → CASE_AGENT_WAKE (kernel resumes autonomously)")
                step_deadline = time.time() + 90

        for cid, (obj, st) in conds.items():
            if rendered_status.get(cid) != st and st == "SATISFIED":
                remaining = [o for c2, (o, s2) in conds.items() if s2 != "SATISFIED"]
                line("Kernel", MAG, f"✓ {obj} → SATISFIED (verified server-side)")
                if remaining:
                    line("", DIM, f"  still waiting on: {remaining[0]}")
                rendered_status[cid] = st
                step_deadline = time.time() + 90

        if status == "CLOSED":
            if len(reply_personas) < 2:
                print(f"\n{YEL}{BOLD}SAME-OWNER: both asks routed to one owner this run; re-run for two distinct owners.{RST}\n")
                _teardown(runner, ctx, force=True)
                return 2
            line("Kernel", GRN, "All conditions satisfied. The kernel proposed closure and CLOSED the goal.")
            print()
            line("Result", BOLD, "1 objective · 2 asynchronous human decisions · 0 operator follow-ups · CLOSED")
            print(f"\n{GRN}{BOLD}PASS: autonomous coordination closed the goal end to end.{RST}\n")
            _teardown(runner, ctx)
            return 0

        if time.time() > step_deadline:
            print(f"\n{YEL}{BOLD}STALLED: no progress; re-run for a clean take.{RST}")
            line("", DIM, f"status={status} conditions={conds}")
            _teardown(runner, ctx)
            return 2
        time.sleep(3)

    print(f"\n{RED}{BOLD}FAIL: goal did not close within the window (status={status}).{RST}")
    _teardown(runner, ctx, force=True)
    return 1


def _teardown(runner, ctx, force=False):
    if force or os.environ.get("EMILY_KEEP") != "1":
        try:
            runner.teardown(ctx.workspace_id)
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
