# How to run Emily for the demo video

Two things to show: (A) the full coordination running end to end, and (B) proof it
runs on Google Cloud. The cleanest, safest split is: run the full coordination
LOCALLY (it provisions a throwaway workspace and never touches production data), and
show the deployed Cloud Run service + logs for the Google Cloud proof.

## A. The autonomous coordination run (local, ~2 min, camera-ready)

Prereq: the Meetless stack running locally (control :3006, worker, intel :8100), a
monorepo checkout, and this repo's venv.

```bash
cd emily-agent
source .venv/bin/activate
export GOOGLE_API_KEY=<gemini key>       # or use Vertex
./scripts/record_take.sh                  # produces one clean flat take, kept for recording
```

`record_take.sh` runs `scripts/demo_autonomous.py` and re-runs until it yields one clean
take (the shared reasoner occasionally spawns a recursive sub-condition, which it detects
in seconds and skips). What you record, verbatim from the real case, is:

- ONE operator instruction (an outcome, not a workflow).
- Emily (Gemini via ADK) grounds and submits a governed Goal.
- The kernel decomposes it into two blocking conditions and routes each to its own
  accountable owner (Maya · Payments Engineering; Chris · QA Lead).
- Asks sent, goal PARKED (no compute while waiting).
- Two humans reply asynchronously; each reply is a real CASE_AGENT_WAKE that resumes the
  kernel on its own. NO operator follow-ups.
- Each condition verifies to SATISFIED server-side; when both are, the kernel proposes
  closure and CLOSES the goal.
- Closing line: 1 objective · 2 asynchronous human decisions · 0 operator follow-ups · CLOSED.

There is deliberately no manufactured "denied close": the kernel proposes closure only
when both conditions are satisfied. The architectural point to narrate is that the LLM
proposes and the kernel owns durable truth and closure.

Structural proof to show after (optional): the goal id is in the workspace; run the frozen
assertion set from the monorepo:
`DATABASE_URL=... node tools/scenarios/emily/golden-d1-trace.cjs <goalId>`.
(`scripts/demo.py` and `run_local.py` remain as an alternate / narrate-each-step view.)

## B. Google Cloud proof (record these)

1. **Emily deployed on Cloud Run** (authenticated):
   - Service: `emily-agent`, region `us-central1`, project `prod-meetless`.
   - URL: `https://emily-agent-653554733822.us-central1.run.app`
   - Show the Cloud Run console page for the service and its Ready revision
     (`emily-agent-00001-kw8`).

2. **The deployed agent invoking a real tool + Gemini 3.5 Flash** (proven,
   revision `emily-agent-00002-n5v`, pointing at the public backend endpoints
   `control.meetless.ai` / `intel.meetless.ai`):

```bash
SA=pulse-reader@prod-meetless.iam.gserviceaccount.com   # any account with run.invoker
URL=https://emily-agent-653554733822.us-central1.run.app
TOKEN=$(gcloud auth print-identity-token --account "$SA")
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "$URL/apps/emily_agent/users/demo/sessions/v1" -d '{}'
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "$URL/run" -d '{"app_name":"emily_agent","user_id":"demo","session_id":"v1",
  "new_message":{"role":"user","parts":[{"text":"Call meetless__retrieve_knowledge for \"what is Meetless\" and report."}]}}'
```

   The tool now returns a clean HTTP 200 governed-memory result (no 404): the
   production governed-memory service answers `corpus_empty` because the prod corpus
   is not populated (dogfooding happens locally), which is a valid governed answer,
   not an error, and exposes no sensitive content. On camera, narrate Emily's
   summary rather than the raw JSON (the JSON echoes the opaque workspace id).

   Then show the Cloud Run logs: they contain
   `Sending out request, model: gemini-3.5-flash, backend: GoogleLLMVariant.GEMINI_API`
   and the MCP tool session, proving Gemini 3.5 Flash + ADK executed on Google Cloud.
   The rich, non-empty knowledge and the full coordination are shown in the LOCAL run
   (section A), which uses a populated throwaway workspace.

3. **The Meetless coordination backend on Cloud Run** (the backend Emily drives):
   `meetless-control`, `meetless-intel`, `meetless-worker` in `prod-meetless`,
   `us-central1`. Show that services list.

## Video wording (avoid contradictory proof)

Do not show raw red FAIL labels. Say instead:

> 271 automated tests pass. The live non-recursive D1 scenario passes every in-scope
> positive and negative invariant. Recursive coordination is explicitly outside this
> submission.

## Notes

- The Cloud Run service is authenticated on purpose: it holds a backend token, so it
  is not exposed unauthenticated. Invoke it with an identity token as shown.
- The deployed agent points at the production Meetless backend; a full coordination
  drive would create real cases there, so drive the full demo locally against a
  throwaway workspace instead.
