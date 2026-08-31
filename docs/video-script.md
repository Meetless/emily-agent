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

## 1:05 to 1:35 — The kernel decomposes and routes to two different owners
The renderer shows the Goal decomposed into two blocking conditions, each routed to a
DIFFERENT accountable owner (Payment retry policy → Maya, Payments Engineering; QA
sign-off → Chris, QA Lead), then "Asks sent. PARKED." Voiceover: "Emily handed the
durable work to the coordination kernel. It broke the outcome into what must be true,
and routed each decision to the person who actually owns it. Two different humans. Now
it parks — no compute while it waits."

## 1:35 to 2:20 — Two asynchronous replies; the kernel resumes itself
The two humans reply (Slack in production; simulated here). Each reply is a real
CASE_AGENT_WAKE that resumes the kernel on its own, and each condition flips to
SATISFIED. Emphasize: NO operator is telling Emily to check again between replies.
Voiceover: "Maya answers the retry policy. That event wakes the workflow and the
condition verifies. Still waiting on QA. Chris signs off. That event wakes it again.
Both conditions are now satisfied — and at no point did anyone prompt Emily to
continue."

## 2:20 to 2:45 — The kernel closes it (LLM proposes, kernel owns truth)
Show "All conditions satisfied. The kernel proposed closure and CLOSED the goal," then
the closing line: 1 objective · 2 asynchronous human decisions · 0 operator follow-ups
· CLOSED. Voiceover: "Emily proposed completion; the coordination kernel decided it.
Gemini reasons about what should happen. The kernel owns durable truth — closing a goal
is a server-side transition guarded by its conditions. Emily cannot hallucinate done."

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
