# Devpost submission text (Emily)

## Tagline
Emily is a background agent that gets work done across a company, coordinating real
people and systems to finish an objective, and she cannot fake completion.

## Inspiration
Most "agentic" demos are chatbots over a knowledge base. But when something actually
has to ship, the hard part is not answering a question. It is figuring out what is
blocking the work, who owns each decision, waiting on people and systems, verifying
what really happened, and keeping the whole dependency chain moving. That is
background work no one wants to do. We built an agent that does it, under governance.

## What it does
You give Emily an objective in plain language: "get the Checkout pilot ready for
Monday." Emily (Gemini, via Google ADK) grounds herself in the company's real state,
launches a coordination Goal, and drives it to completion:

- The coordination kernel autonomously decomposes the Goal into the Conditions that
  must be true, and routes each decision to its accountable owner.
- Emily supervises: she approves the outreach the kernel proposes, and waits when a
  decision belongs to a human, rather than inventing it.
- Owners reply where they already work (Slack); the kernel records their
  authoritative decisions and verifies each Condition against the evidence.
- When everything is satisfied, Emily proposes closing the Goal. A server-side
  structural gate decides. If a Condition is still open, it returns "not_ready" and
  refuses. Emily is structurally incapable of declaring a Goal done herself.

## How we built it
- Reasoning: Google Gemini (gemini-3.5-flash)
- Agent framework: Google ADK (Agent Development Kit)
- Cloud: Google Cloud Run
- Coordination backend: Meetless, our pre-existing production change-governance
  platform (control + worker + intel on Cloud Run), integrated over its public Model
  Context Protocol (MCP) interface.

Architecture is "one planner, one source of truth." Emily plans the operator work and
selects tools; Meetless is the durable coordination runtime and the guardrail. We
added a thin, generally-useful set of coordination verbs to the Meetless MCP server
(submit goal, read state, list proposals, review, propose close). Emily is given only
those five verbs plus knowledge retrieval; the kernel's in-case planner verbs are
deliberately not exposed to her, so she can drive the coordination but never race the
kernel or corrupt a case.

## Disclosure (hackathon rules)
The submitted agent (this repository) was newly built during the submission period.
It integrates with Meetless, a pre-existing platform owned by the submitting team,
disclosed here as incorporated pre-existing work.

## Challenges
The agent must never become a second brain. The coordination kernel is already an
autonomous planner, so we designed Emily as a governed driver, verified against the
real system, and encoded the boundary as a test that forbids exposing the kernel's
planner verbs.

## What's next
Multi-surface intake (Slack, email, doc) into the same agent, and deeper grounding so
Emily discovers decision owners from the company's real ownership records.

## Try it
Repo README has local setup and an end-to-end demo that drives a real coordination
Goal to CLOSED. Video shows the live run plus the Cloud Run deployment.

## Technologies used
Google Gemini 3.5 Flash, Google ADK, Model Context Protocol, Google Cloud Run,
Python, Node.js, NestJS, FastAPI, PostgreSQL.
