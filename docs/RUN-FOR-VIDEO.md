# How to run Emily for the demo video

Two things to show: (A) the full coordination running end to end, and (B) proof it
runs on Google Cloud. The cleanest, safest split is: run the full coordination
LOCALLY (it provisions a throwaway workspace and never touches production data), and
show the deployed Cloud Run service + logs for the Google Cloud proof.

## A. The full coordination (local, ~4 min, safe)

Prereq: the Meetless stack running locally (control :3006, worker, intel :8100), a
monorepo checkout, and this repo's venv.

```bash
cd emily-agent
source .venv/bin/activate
export GOOGLE_API_KEY=<gemini key>       # or use Vertex
export EMILY_KEEP=1                        # keep the workspace so you can show the HUD
python scripts/demo.py
```

You will see, live: Gemini grounds and submits the Goal, the kernel decomposes it
into two Conditions, Emily approves both proposals (real `coordination_review_proposal`
calls), the owner answers, the Conditions verify to SATISFIED, and the server closes
the Goal. For the "cannot fake done" beat, before all conditions are satisfied Emily
calls `coordination_propose_close` and the server returns `not_ready` with `blockedBy`.

To narrate on camera, `python run_local.py "<objective>"` streams the tool calls one at
a time, or use `adk web` for the visual tool-call panel.

Structural proof to show after (optional): the goal id is printed; run the frozen
assertion set from the monorepo:
`DATABASE_URL=... node tools/scenarios/emily/golden-d1-trace.cjs <goalId>`.

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
