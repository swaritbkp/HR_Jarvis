# HR Jarvis

A generator that scaffolds a governed, 40-agent HR stack into a Google Antigravity workspace.

## What it is

This repo contains a Python generator. Run it and it writes out a complete Antigravity workspace: a 40-agent registry, eight functional groups, personas with RBAC scoping, approval gates on the agents that touch people's careers and pay, an append-only audit log, small-cell masking, a Stitch UI pipeline, and a working PERT/CPM planner.

The starting point is a public landscape diagram, "40 AI Agents Transforming Modern HR", which lays out five layers: a strategic core, an orchestration and governance layer, twenty employee-facing agents, twenty people-i…


## Design rule: the model proposes, code decides

Nothing in this stack is an LLM with write access to an HR system.

- The 40 agents are deterministic Python. Given the same input they produce the same output. No LLM runs inside an agent.
- Where language work is genuinely needed (drafting, summarising, reading unstructured text), a Gemini layer proposes. The proposal comes back as structured data and is validated by code before anything acts on it.
- Anything that touches a person's employment, pay or record stops at an approval gate.

That split is the whole design. It means the system can be tested, audited, and explained six months later without reconstructing a prompt.

## What it generates

- *Agent registry.* 40 agents defined once, in one place, as the single source of truth. Everything else reads from it.
- *Eight groups* mapped onto the slide's five layers, so the diagram and the code describe the same system.
- *Personas and RBAC.* Every agent runs as a persona with a defined scope. Access is deny-by-default.
- *Approval gates on eight agents:* screening, offer letter, pay equity, attrition risk, investigation, succession, case triage, and the sandbox. These cannot complete without a named human approver.
- *Append-only audit.* Every action, proposal, approval and refusal is written to a log that cannot be edited in place.
- *Small-cell masking.* Any cohort below five people is masked in aggregate output, so a report cannot be used to identify one employee.
- *Stitch UI pipeline.* The interface layer is generated from the registry, so the UI cannot drift away from the agent definitions.
- *PERT/CPM planner.* A deterministic scheduler for HR programmes, with dependency resolution and a computed critical path.


## Why the governance is the interesting part

An HR agent is not a chatbot with a personality. It sits between an employee and a decision about that employee. Four things have to be true before it is allowed to act:

1. *It can only see what its persona is scoped to see.* A benefits agent does not get to read an investigation file because it was convenient.
2. *It cannot act alone on anything irreversible.* Eight agents are gated, and the gate names a human.
3. *It writes everything down.* The audit log is append-only, so the record of what happened is not something the system can tidy up later.
4. *It refuses rather than guesses.* When the model's proposal fails validation, the pipeline halts and returns an explicit "insufficient basis" instead of a plausible answer.

Point four is the one people skip. A system that always answers is a system you cannot trust with payroll.

## What this is not

- Not a product, and not connected to any live HR system.
- Not running on real employee data. Everything runs on synthetic data, labelled as synthetic in the generated workspace.
- Not a claim that any of the 40 agents are production-ready. They are a working scaffold with real governance, not a shipped service.
- Not a fine-tuned model. There is no fine-tuning anywhere in this build. The intelligence sits in a routing and validation layer over an off-the-shelf model, plus deterministic code doing the deciding.

## Running it

```bash
python hr_agent_stack_antigravity_setup.py
```

Then open the generated workspace in Antigravity.

## Status

Working scaffold. The governance layer, registry, planner and masking are complete and tested. The agent logic itself is deliberately thin: it exists to prove the control plane, not to replace an HRIS.
