# Emily demo video shot list (target 3:40, hard cap 4:00)

Rules from the judge Q&A: wow in the first 30 seconds; real human voice (no AI
voice); one strong end-to-end workflow; show the Cloud Run dashboard for the GCP
proof; the video is graded, so the live run must read clearly.

Setup before recording: control + worker + intel running locally; `adk web` open
on the emily_agent app; `scripts/demo.py` ready in a terminal; a browser tab on the
prod-meetless Cloud Run dashboard.

## 0:00 to 0:25 — Cold open (the wow)
Type the ask to Emily: "Get the Checkout pilot ready for the Monday beta. The
payment retry policy and the provider timeout budget are still open." Voiceover:
"This is not a chatbot. Emily gets the work done across a company, and she cannot
fake that it is done."

## 0:25 to 1:05 — Gemini grounds and launches
Show Emily's tool calls live (adk web or the run_local trace): retrieve_knowledge,
then coordination_submit_goal. Point out the goal id. Voiceover: "Gemini interprets
the objective and launches a governed coordination Goal. It does not plan the whole
thing itself; it hands the durable work to the kernel."

## 1:05 to 1:45 — The kernel decomposes; Emily supervises
Show coordination_get_state returning the two Conditions, and Emily calling
coordination_review_proposal to approve the kernel's outreach. Voiceover: "The
kernel decomposed the goal into the conditions that must be true and proposed who to
ask. Emily approves the on-objective outreach. This is a real approval call, not a
narration."

## 1:45 to 2:20 — The accountable human answers; the case resumes
Show the owner's authoritative reply going in (Slack in the real product; the demo
harness simulates it), then coordination_get_state showing a Condition flip to
SATISFIED. Voiceover: "Emily waited on the accountable owner rather than inventing
the decision. Their answer is captured as authoritative evidence, and the durable
case resumes on its own."

## 2:20 to 2:45 — The can't-lie beat (signature)
Intentional red-team probe: while one Condition is still open, have Emily call
coordination_propose_close. Show the server returning status "not_ready" with
blockedBy. Voiceover: "Watch what happens when we ask Emily to close early. The
server refuses. Emily cannot declare a goal done. Only the server can, and only when
the evidence supports it." (Frame this explicitly as a deliberate safety probe.)

## 2:45 to 3:10 — Finish the work; server closes
The second owner answers, the last Condition verifies, Emily proposes closure again,
and now the server returns "closed". Show the goal status CLOSED and the HUD / audit
trail. Voiceover: "Every decision has an accountable owner and a verification. The
whole chain is auditable."

## 3:10 to 3:30 — Architecture + Google Cloud proof
Show the README architecture diagram (Gemini + ADK + MCP + Meetless kernel), then
switch to the prod-meetless Cloud Run dashboard (meetless-control / meetless-intel /
meetless-worker, Ready). Voiceover: "Gemini 3.5 Flash via Google ADK drives the
operator loop; the Meetless coordination kernel runs on Google Cloud Run."

## 3:30 to 3:40 — Thesis
"Ask your company. Emily does not just answer. She coordinates, waits, verifies,
finishes, and she cannot fake done."

## Proof to keep alongside the video
- goal/case id + timestamps, the ADK tool-call trace, the proposal approval call,
  the owner reply, the SATISFIED transitions (via condition_verify), the not_ready
  refusal, the structural close (reason goal_resolved), final HUD.
- Sanitize workspace ids / tokens before publishing.
