#!/usr/bin/env python3
"""
hr_agent_stack_antigravity_setup.py

V2 (hackathon edition). Adds Google Stitch UI pipeline, Gemini guardrails ("model proposes,
code decides"), judged-axis scorecard, PERT/CPM sprint planner, pitch kit and a self-check.

Generates an Antigravity-ready project skeleton for the "40 AI Agents for HR" demo:
  - .agent/rules/      always-on project rule
  - .agent/skills/     8 skills (architecture, data, agent framework, Jarvis router,
                       portal, governance, cloud deploy, testing)
  - .agent/workflows/  slash commands (/hr-build-all, /hr-database, /hr-jarvis, ...)
  - spec/              agents.json (40-agent registry), personas.json, layers.json, PRD.md

Usage:
  python setup_hr_agents_antigravity.py                      # -> ./hr-agent-stack
  python setup_hr_agents_antigravity.py --target ~/work/hr   # custom folder
  python setup_hr_agents_antigravity.py --both               # write .agent/ AND .agents/
  python setup_hr_agents_antigravity.py --force              # overwrite existing files

Python 3.9+, standard library only.
"""
import argparse
import json
import re
from pathlib import Path

# ----------------------------------------------------------------------------
# 1. REGISTRY: 40 agents (source of truth that Antigravity builds against)
# ----------------------------------------------------------------------------
SENSITIVE = {
    "Resume Screening Agent", "Offer Letter Agent", "Pay Equity Analysis Agent",
    "Attrition Risk Agent", "Investigation Doc Agent", "Succession Mapping Tool",
    "Case Triage & Routing Agent", "Sandbox Agent",
}

GROUPS = [
    dict(layer="Employee-facing", group="Talent", kind="workflow+docgen",
         tables=["requisitions", "candidates", "interviews", "salary_bands"],
         tools=["ATS", "calendar", "email"], scope="Candidate records", approver="hr_head",
         agents=[
             ("Sourcing Agent", "Find Relationship Manager candidates for Ludhiana",
              "Rank talent-pool candidates by role, skill and city match; return top 5 with match score"),
             ("Resume Screening Agent", "Screen applicants for the Relationship Manager role",
              "Score applicants against requisition criteria with visible reasons; never auto-reject, queue an approval"),
             ("Scheduling Agent", "Book interviews for the shortlisted candidates",
              "Find free slots across panel availability; insert interviews rows; return the slots"),
             ("Candidate Q&A Agent", "Candidate asks what the hiring timeline is",
              "Look up candidate stage; answer from a stage-timeline FAQ; escalate salary questions to recruiter"),
             ("Offer Letter Agent", "Draft an offer for the selected candidate",
              "Fill offer template from candidate plus salary band; status pending_approval"),
         ]),
    dict(layer="Employee-facing", group="Onboarding", kind="workflow",
         tables=["onboarding_tasks", "employees"], tools=["HRIS", "IT desk", "calendar"],
         scope="New joiner and their manager", approver="hr_ops",
         agents=[
             ("Pre-boarding Agent", "What does a new joiner need before Day 1?",
              "Return pre-join checklist from onboarding_tasks template for the joiner"),
             ("Day-1 Orchestration Agent", "Set up this Monday's joiners",
              "Create Day-1 task set (IT access, desk, buddy, induction) per joiner; return schedule"),
             ("Buddy/Mentor Match Agent", "Match a buddy for the new RM in Amritsar",
              "Pick senior employee in same branch and role family, tenure >= 3 yrs, lowest buddy load"),
             ("30/60/90 Check-in Agent", "Run the 30-day check-in",
              "Select joiners at day 30/60/90; create check-in tasks; summarise open blockers"),
             ("New Hire Status Bot", "Where is my laptop request?",
              "Look up the joiner's onboarding task by keyword; return status and ETA"),
         ]),
    dict(layer="Employee-facing", group="Talent Mgmt & Dev", kind="recommend",
         tables=["employees", "skills", "performance_reviews", "requisitions"],
         tools=["HRIS", "LMS"], scope="Own data; manager sees own team", approver="hrbp",
         agents=[
             ("Career Path Agent", "What roles can I grow into?",
              "Map current grade to next grades via career ladder; compute skill gaps from skills table"),
             ("Mobility Match Agent", "Show open roles that match my profile",
              "Match employee skills to open requisitions; top 3; do not notify manager without consent flag"),
             ("Skills Inventory Agent", "Which teams have compliance-certified staff?",
              "Aggregate skills and certifications by branch/department; flag gaps"),
             ("Conversation Prep Agent", "Prep me for an appraisal conversation",
              "Assemble last ratings, goals and achievements into a talking-points template"),
             ("Succession Mapping Tool", "Who can succeed the Branch Manager?",
              "Rank by grade, rating, tenure; bucket ready-now vs ready-in-12-months"),
         ]),
    dict(layer="Employee-facing", group="Business Partners", kind="analytics+summary",
         tables=["employees", "engagement_pulses", "exit_interviews", "requisitions"],
         tools=["HRIS", "survey tool"], scope="Aggregated, small groups masked", approver="hrbp",
         agents=[
             ("HRBP Briefing Agent", "Brief me on the Punjab region",
              "Aggregate attrition, open requisitions and engagement for a region; one-page summary"),
             ("Coaching Support Tool", "Help a manager give tough feedback",
              "Return a structured feedback framework (situation, behaviour, impact) filled with context"),
             ("Engagement Pulse Agent", "Run a pulse for the branch teams",
              "Create a pulse; compute response rate and average score by branch"),
             ("Listening Synthesis Agent", "Summarise the exit-interview themes",
              "Group exit_interviews by theme; counts and top themes; no names"),
             ("Team Health Agent", "How is the Jalandhar branch doing?",
              "Compute workload (leave, overtime), engagement and attrition flags; aggregate only, mask n<5"),
         ]),
    dict(layer="People infrastructure", group="People Operations", kind="rag+routing",
         tables=["policies", "tickets", "cases", "case_events"],
         tools=["Policy library", "ticketing"], scope="Own records only", approver="hr_head",
         agents=[
             ("Policy Q&A Agent", "How many casual leaves do I get?",
              "Keyword/BM25 search over policies; return clause, version and last-updated date"),
             ("HR Service Desk Agent", "Send me my March salary slip",
              "Match intent to service catalogue; create and close ticket; return synthetic doc link"),
             ("New Hire Provisioning Agent", "Provision accounts for 4 joiners",
              "Create account records (email, CRM, HRIS) for joiners; write audit entries"),
             ("Case Triage & Routing Agent", "An employee has raised a grievance",
              "Classify by keyword rules (conduct, pay, safety, other); set priority; route to owner"),
             ("Investigation Doc Agent", "Compile the case file for review",
              "Build timeline from case_events into a document template; HR owns conclusions"),
         ]),
    dict(layer="People infrastructure", group="Total Rewards", kind="rag+analysis",
         tables=["salary_bands", "compensation", "benefits", "employees", "esop_grants"],
         tools=["Payroll", "comp data"], scope="Role-based; comp team only for cohorts", approver="comp_lead",
         agents=[
             ("Salary Banding Agent", "Which band fits this role?",
              "Map role and grade to salary_bands; show range and compa-ratio"),
             ("Pay Equity Analysis Agent", "Check pay gaps in the RM cohort",
              "Compare pay by gender within grade and role; flag outliers over threshold; mask small groups"),
             ("Benefits Q&A Agent", "What does my health cover include?",
              "Look up benefits plan text; return coverage and claim steps"),
             ("Equity Education Agent", "Explain my ESOP vesting",
              "Compute vesting schedule from esop_grants; plain-language explainer"),
             ("TR Statement Agent", "Generate my total rewards statement",
              "Assemble base, variable, benefits value and ESOP into a statement document"),
         ]),
    dict(layer="People infrastructure", group="People Analytics", kind="analytics",
         tables=["employees", "exits", "requisitions", "engagement_pulses", "compensation"],
         tools=["Warehouse (read-only)"], scope="Role-scoped; groups under 5 masked", approver="hrbp",
         agents=[
             ("NL Query Agent", "Headcount by branch in North Haryana",
              "Map question to whitelisted parameterised queries (headcount, attrition, tenure) by dimension; show the SQL"),
             ("Attrition Risk Agent", "Which teams are at risk of attrition?",
              "Rule-based risk score (tenure, rating, engagement, compa-ratio) aggregated per team; no individual verdicts"),
             ("Workforce Reporting Agent", "Show the monthly HR dashboard",
              "Compute hires, exits, vacancies and headcount trend for the month"),
             ("Headcount Modeling Agent", "Plan 15% growth next year",
              "Scenario calc: target headcount, hires needed, cost using band midpoints"),
             ("Predictive Modeling Agent", "Forecast hiring needs for next quarter",
              "Trend plus attrition-rate projection with a range"),
         ]),
    dict(layer="People infrastructure", group="HR Technology", kind="monitor",
         tables=["integrations", "employees", "audit_log"],
         tools=["Integration logs", "audit log"], scope="System metadata", approver="governance",
         agents=[
             ("Data Quality Agent", "Check the HRIS for errors",
              "Run rules (missing manager, null dates, duplicate emails); list records and proposed fixes"),
             ("Integration Health Agent", "Is the payroll sync working?",
              "Read integrations table; return status, last_sync and lag"),
             ("Agent Performance Monitor", "How are the agents performing?",
              "Aggregate audit_log: runs, success rate, escalations, average latency per agent"),
             ("Sandbox Agent", "Test a new policy safely",
              "Run a draft policy through a test harness on synthetic data in a flagged, isolated scope"),
             ("Documentation Agent", "Document the onboarding workflow",
              "Generate a markdown document from the agent registry and workflow config"),
         ]),
]

LAYERS = [
    {"name": "Strategic core", "type": "human", "roles": ["CHRO & Executive Leadership"]},
    {"name": "Orchestration & governance", "type": "human",
     "roles": ["AI Transformation Lead", "AI Product Manager",
               "Governance & Compliance Lead", "Agent Builder / Technical Lead"]},
    {"name": "Employee-facing", "type": "agents", "groups": ["Talent", "Onboarding", "Talent Mgmt & Dev", "Business Partners"]},
    {"name": "People infrastructure", "type": "agents", "groups": ["People Operations", "Total Rewards", "People Analytics", "HR Technology"]},
    {"name": "Foundation", "type": "platform",
     "modules": {"Knowledge & Data": "Postgres + policy search", "Identity & Access": "demo personas + RBAC",
                 "Audit & Trust": "audit_log + approvals", "Integration Hub": "integrations table + mock connectors"}},
]

PERSONAS = [
    {"id": "chro", "name": "CHRO", "allow_groups": "*", "note": "Sees everything, can approve anything"},
    {"id": "hr_head", "name": "HR Head", "allow_groups": "*", "note": "Approves offers, cases, policy actions"},
    {"id": "hrbp", "name": "HR Business Partner", "allow_groups": ["Business Partners", "Talent Mgmt & Dev", "People Operations", "People Analytics"]},
    {"id": "recruiter", "name": "Recruiter", "allow_groups": ["Talent", "Onboarding"]},
    {"id": "comp_lead", "name": "Total Rewards Lead", "allow_groups": ["Total Rewards", "People Analytics"], "note": "Approves pay-equity outputs"},
    {"id": "manager", "name": "Line Manager", "allow_groups": ["Talent Mgmt & Dev", "Business Partners", "Onboarding"], "note": "Team-scoped data only"},
    {"id": "employee", "name": "Employee (Priya Sharma)", "allow_groups": ["People Operations", "Total Rewards", "Talent Mgmt & Dev", "Onboarding"],
     "allow_agents": ["policy-q-and-a-agent", "hr-service-desk-agent", "benefits-q-and-a-agent", "equity-education-agent",
                      "tr-statement-agent", "career-path-agent", "mobility-match-agent", "conversation-prep-agent",
                      "new-hire-status-bot"], "note": "Self-scoped: only their own records"},
    {"id": "governance", "name": "Governance & Compliance Lead", "allow_groups": ["HR Technology"], "note": "Audit log, approvals oversight, monitor agents"},
]


def slug(name):
    s = name.lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def build_registry():
    out = []
    for g in GROUPS:
        for name, ask, logic in g["agents"]:
            out.append({
                "id": slug(name), "name": name, "group": g["group"], "layer": g["layer"],
                "kind": g["kind"], "ask": ask, "logic": logic,
                "tables": g["tables"], "tools": g["tools"], "scope": g["scope"],
                "approval": "required" if name in SENSITIVE else "auto",
                "approver": g["approver"], "uses_llm": False, "version": "1.0.0",
            })
    assert len(out) == 40, len(out)
    return out


# ----------------------------------------------------------------------------
# 2. ALWAYS-ON RULE
# ----------------------------------------------------------------------------
RULE = r'''---
trigger: always_on
description: Project rules for the HR Agent Stack demo (synthetic data, 40 deterministic agents, Jarvis router)
---

# HR Agent Stack: project rules

**What we are building:** an end-to-end demo of the "40 AI Agents Transforming Modern HR" stack for a CHRO.
Cloud-hosted web portal + backend + synthetic database + 40 agents + one central "Jarvis" router agent.

## Non-negotiables
1. **Synthetic data only.** No real employee data, ever. Show a visible "Synthetic data" banner in the UI.
2. **Source of truth is `spec/`:** `spec/agents.json` (the 40 agents), `spec/personas.json`, `spec/layers.json`, `spec/PRD.md`.
   Never invent, rename or drop an agent; ids must match `agents.json`.
3. **Agents are deterministic Python** (SQL, rules, templates, search). No LLM calls inside the 40 agents.
   Jarvis may use an optional LLM only behind `USE_LLM=true` (default `false`). The demo must work with no API key.
4. **Simplest scalable solution first.** One repo, one container serving API + built frontend, one Postgres.
5. **Every agent run writes to `audit_log`.** Agents with `approval: required` return `pending_approval` and create an `approvals` row.
6. **Jarvis never executes silently.** It proposes a route; the UI shows a confirm card; only then the agent runs.
7. **Privacy by design:** persona scoping on every query; aggregate results with group size < 5 are masked.
8. **No secrets in code.** Use env vars; keep `.env.example` current.

## Stack defaults
- Backend: Python 3.12, FastAPI, SQLAlchemy 2, psycopg 3, Pydantic v2, pytest.
- DB: PostgreSQL (Neon or Supabase free tier for the demo; SQLite allowed for local dev only).
- Frontend: React + Vite + TypeScript + Tailwind. Mobile-first, responsive, works on a phone.
- Deploy: single Docker image to Google Cloud Run (Render is the fallback).

## How to work
- Prefer the slash commands in `.agent/workflows/`. Start with `/hr-status`, then `/hr-build-all`.
- Load the matching skill from `.agent/skills/` before each stage. Read `SKILL.md` first.
- After each stage: run tests, summarise what changed, list anything not done. Do not skip ahead.
- Ask the user before any deploy, any paid service, or any destructive command.
'''

# ----------------------------------------------------------------------------
# 3. SKILLS
# ----------------------------------------------------------------------------
SKILLS = {}

SKILLS["hr-stack-architecture"] = ("Use when planning or changing the overall structure of the HR agent demo: layers, repo layout, API contract and how the slide's 5 layers map to code.", r'''
# HR stack architecture

## Slide layer -> code mapping
| Slide layer | In this project |
|---|---|
| Strategic core (CHRO) | Persona `chro`; executive dashboard page |
| Orchestration & governance | Jarvis router + approvals queue + audit page; personas for AI Transformation, Governance |
| Employee-facing (20 agents) | `backend/app/agents/employee_facing/*.py` |
| People infrastructure (20 agents) | `backend/app/agents/people_infra/*.py` |
| Foundation | `db.py` (Knowledge & Data), `governance/rbac.py` (Identity & Access), `governance/audit.py` (Audit & Trust), `integrations/` (Integration Hub) |

## Repo layout
```
spec/                 agents.json, personas.json, layers.json, PRD.md
backend/
  requirements.txt
  app/
    main.py           FastAPI app; mounts /api and serves ../static (built frontend) with SPA fallback
    config.py         env settings
    db.py  models.py  SQLAlchemy engine + models
    seed/             synthetic data generator (seed.py, stories.py)
    agents/           base.py, registry.py, employee_facing/, people_infra/
    jarvis/           router.py, entities.py
    governance/       rbac.py, audit.py, approvals.py
    api/              routes_*.py
  tests/
frontend/             Vite React TS app
Dockerfile  docker-compose.yml  .env.example  README.md
```

## API contract (do not change without updating the frontend)
- `GET  /api/health`
- `GET  /api/personas`
- `GET  /api/agents` (filtered by header `X-Persona`)
- `POST /api/jarvis/route` body `{message}` -> `{agent_id, agent_name, confidence, params, alternatives:[{agent_id,agent_name,confidence}], needs_confirmation:true, reply}`
- `POST /api/agents/{agent_id}/run` body `{params, confirmed:true}` -> `{run_id, status:"completed"|"pending_approval"|"denied", result, sql?, audit_id}`
- `GET  /api/approvals`, `POST /api/approvals/{id}/decide` body `{decision:"approve"|"reject", note}`
- `GET  /api/audit?agent_id=&limit=`
- `GET  /api/dashboard/summary`

## Result schema (every agent returns this shape)
```json
{"kind":"text|table|checklist|doc|chart","title":"...","summary":"one-line answer",
 "data":{"columns":[],"rows":[]}, "sql":"optional shown for audit", "notes":["masking applied", "..."]}
```
Persona is passed in header `X-Persona` (demo auth). In production this would be SSO claims.
''')

SKILLS["hr-synthetic-data"] = ("Use when designing the database schema or generating synthetic HR data, including the planted demo 'stories'.", r'''
# Synthetic HR database

Generate with `Faker("en_IN")` and a **fixed seed** so every run is identical. Company: "Centricity WealthTech (demo)", set via `COMPANY_NAME`.

## Tables (minimum)
`branches, departments, employees, salary_bands, compensation, esop_grants, leave_balances, leave_requests, performance_reviews, skills, career_ladder, requisitions, candidates, interviews, panel_availability, onboarding_tasks, engagement_pulses, exit_interviews, exits, policies, benefits, tickets, cases, case_events, integrations, accounts, audit_log, approvals, agent_runs, personas`

Key columns:
- `employees(id, name, email, role, grade, department_id, branch_id, manager_id, hire_date, status, gender, salary_band_id)`
- `salary_bands(id, grade, min_inr, max_inr)`; `compensation(employee_id, base, variable, effective_from)`
- `candidates(id, name, role_applied, city, skills[], experience_yrs, stage, source, applied_on)`
- `policies(id, title, category, body, version, updated_at)`: 25+ realistic policies (leave, travel, code of conduct, WFH, POSH, expense, notice period)
- `audit_log(id, ts, persona, agent_id, action, params_json, status, latency_ms, approval_id)`
- `approvals(id, audit_id, agent_id, requested_by, approver_persona, status, decided_by, decided_at, note)`

## Volumes
~600 employees, 14 branches (Chandigarh, Mohali, Panchkula, Ludhiana, Jalandhar, Amritsar, Patiala, Bathinda, Ambala, Karnal, Panipat, Kurukshetra, Hisar, Rohtak), 8 departments, 12 roles (Relationship Manager, Senior RM, Investment Counsellor, Branch Manager, Operations Executive, Compliance Officer, HR Executive, Regional Head, etc.), 18 open requisitions, 120 candidates, 12 months of pulses, 60 exits.
Salaries in INR, realistic bands by grade.

## Planted stories (the demo depends on these)
1. **Jalandhar branch** has high attrition risk: low pulse scores, heavy overtime, 6 exits in 12 months.
2. **Pay-equity outlier:** within the RM cohort, a ~9% gender pay gap at one grade, only visible in aggregate.
3. **ATS sync** in `integrations` is delayed (2h lag); everything else healthy.
4. **Data quality:** exactly 37 employee records with missing manager/date/duplicate email.
5. **Open grievance case** (conduct, priority high) with 4 timeline events.
6. **Priya Sharma**, an RM in Ludhiana, is the employee persona: has leave balances, ESOP grant, benefits, a career path.
7. **3 joiners starting Monday** with onboarding tasks in different states (laptop request pending).
8. A strong internal succession candidate for Branch Manager, Chandigarh.

Mask any aggregate group with n < 5. Provide `python -m backend.app.seed.seed --reset` and idempotent re-seeding.
''')

SKILLS["hr-agent-framework"] = ("Use when implementing or modifying any of the 40 HR agents: base class, registry, handler pattern, approval and audit hooks.", r'''
# Agent framework (deterministic, no LLM)

## Contract
```python
# backend/app/agents/base.py
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Ctx:
    db: Any            # SQLAlchemy session
    persona: str       # chro | hr_head | hrbp | recruiter | comp_lead | manager | employee | governance
    user_id: int | None = None

@dataclass
class Result:
    kind: str          # text | table | checklist | doc | chart
    title: str
    summary: str
    data: dict = field(default_factory=dict)
    sql: str | None = None
    notes: list[str] = field(default_factory=list)

class Agent:
    id: str            # must equal an id in spec/agents.json
    def run(self, ctx: Ctx, params: dict) -> Result: ...
```

## Registry
```python
# backend/app/agents/registry.py
REGISTRY: dict[str, Agent] = {}
def register(agent_id):
    def deco(cls):
        cls.id = agent_id; REGISTRY[agent_id] = cls(); return cls
    return deco
```
Load `spec/agents.json` at startup and **fail fast** if any of the 40 ids has no registered class.

## Rules
- One file per group (e.g. `talent.py` holds the 5 Talent agents). Each agent is a small class with `@register("sourcing-agent")`.
- Implement the behaviour in the `logic` field of that agent in `spec/agents.json`. Read it first.
- Use parameterised SQL or SQLAlchemy only. `NL Query Agent` maps questions to a **whitelist** of query templates, never free SQL.
- Always return a `summary` sentence that answers the question directly, plus `data` for the detail.
- Apply persona scoping through `governance/rbac.py` helpers (employee sees own row; manager sees own team).
- Mask aggregates where group size < 5 and add a note.
- Wrap execution in `run_agent()` (in `governance/audit.py`): checks RBAC, times the run, writes `audit_log`, and for `approval: required` agents returns `pending_approval` and inserts an `approvals` row instead of finalising.
- Text/doc outputs come from Jinja2 templates in `backend/app/agents/templates/`. No LLM.

## Adding or changing an agent
1. Update `spec/agents.json` (only if the user asks), 2. implement the class, 3. add a pytest case using the agent's `ask`, 4. run `/hr-test`.
''')

SKILLS["jarvis-router"] = ("Use when building or tuning Jarvis, the central router agent that interprets a user message, picks one of the 40 agents, and asks the user to confirm on the web page.", r'''
# Jarvis: central router

## Behaviour
1. User types a message in the portal chat.
2. `POST /api/jarvis/route` returns the best agent, confidence, extracted parameters and 2 alternatives.
3. The UI shows a **confirm card**: "I'll use *Attrition Risk Agent* with {region: Punjab}. Confirm / Change agent / Edit".
4. On confirm, the UI calls `/api/agents/{id}/run`. Result is rendered below the card.
5. Jarvis never runs an agent without `confirmed: true`.

## Routing algorithm (no LLM required)
- Build a document per agent from: name + `ask` + `logic` + a hand-written keyword list per agent (keep in `jarvis/keywords.py`).
- Score with TF-IDF cosine (pure Python or scikit-learn) plus: +boost for exact keyword hits, +boost if the agent is allowed for the persona, -penalty if not allowed.
- Confidence = softmax or normalised top score. If top confidence < 0.35 or top-2 gap < 0.05, set `reply` to ask a clarifying question and return the top 3.
- Fallback agent: HR Service Desk Agent.
- Entity extraction (`jarvis/entities.py`): gazetteers loaded from the DB for branch, region (Punjab / North Haryana / Chandigarh), role, department; regex for numbers, percentages, months, employee names. Put results in `params`.
- Optional: if `USE_LLM=true` and an API key exists, use an LLM only to re-rank the top 3. Default off.

## Persona rules
- Respect RBAC: never route to an agent the persona cannot use; say so politely and suggest who can.
- Greeting / small talk / "what can you do?" -> reply with a short capability summary grouped by the 5 layers, no agent run.

## Quality bar
Every agent's `ask` string in `spec/agents.json` must route top-1 to its own agent (>= 38 of 40) and top-3 for all 40. Add this as a pytest. Also test 20 paraphrases written by you.
''')

SKILLS["hr-portal-frontend"] = ("Use when building or changing the React web portal: Jarvis chat with confirm card, agent catalog (the slide), approvals, audit, dashboard, persona switcher.", r'''
# Portal frontend

React + Vite + TypeScript + Tailwind. Mobile-first. If a `frontend-design` skill is available, load it and make deliberate, non-generic design choices suited to an HR/people product for a CHRO audience. Calm, credible, readable. No default template look.

## Pages
1. **Jarvis (home):** chat thread, suggested-prompt chips taken from agents' `ask` strings, **confirm card** before each run (agent name, layer, parameters, Confirm / Change / Cancel), then the result card (summary first, table/checklist/doc below, "SQL used" expandable, approval status badge).
2. **Agent catalog:** reproduces the slide: 5 layers; clickable agent chips in 8 groups; clicking opens a drawer with description, tools, scope, approval rule, sample ask and a "Try it" button that pre-fills Jarvis.
3. **Approvals:** pending items for the current persona with Approve / Reject + note. Switching persona to the approver (e.g. HR Head) must make the item actionable.
4. **Audit & trust:** filterable log (persona, agent, status, latency) with expandable params and outcome.
5. **Dashboard:** CHRO view: headcount, attrition by branch, open reqs, agent usage, integration health.

## Global UI
- Persona switcher in the header (calls `X-Persona`). Persistent "Synthetic data" banner.
- Loading, empty and error states for every call; explain what went wrong and what to do.
- Table results are horizontally scrollable on mobile; keep touch targets >= 44px; visible keyboard focus.
- API base is relative (`/api`) so the same build works locally (Vite proxy) and in the container.
- Typed client in `frontend/src/api.ts` matching the contract in the architecture skill.
''')

SKILLS["hr-governance-audit"] = ("Use when implementing RBAC, persona scoping, audit logging, approvals or data masking for the HR agents.", r'''
# Governance, audit and trust

- **RBAC:** `governance/rbac.py` loads `spec/personas.json`. `can_run(persona, agent)` honours `allow_groups` (`"*"` = all) and `allow_agents`. Deny with HTTP 403 and an audit row (`status=denied`).
- **Row scoping:** employee persona -> only their own `employee_id`; manager -> own reporting line; others per group scope in `agents.json`.
- **Masking:** any aggregate with fewer than 5 people returns "suppressed (n<5)".
- **Audit:** every run inserts `audit_log` (persona, agent, params, status, latency, approval_id). Audit rows are append-only; no update/delete endpoints.
- **Approvals:** agents with `approval: required` produce a draft result stored in `agent_runs`, status `pending_approval`, and an `approvals` row addressed to the group's `approver` persona (CHRO and HR Head can always approve). On approve, mark the run `completed` and write a second audit row. On reject, mark `rejected` with the note.
- **Human-in-the-loop messaging:** sensitive agents (screening, attrition, pay equity, investigation, succession, case triage) must say in the result notes that outputs are decision support and a human decides.
- **No individual predictions:** Attrition Risk reports team-level risk only.
''')

SKILLS["hr-cloud-deploy"] = ("Use when containerising, configuring cloud Postgres, or deploying the HR demo to Cloud Run (or Render).", r'''
# Cloud deploy (single container + hosted Postgres)

## Topology
Browser -> **Cloud Run service** (FastAPI serving `/api` and the built React app from `/static`) -> **Neon or Supabase Postgres**.

## Dockerfile (multi-stage)
```
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY spec/ spec/
COPY --from=web /web/dist ./static
ENV PORT=8080
CMD ["sh","-c","uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
```
Ensure `backend/__init__.py` and `backend/app/__init__.py` exist.

## Environment variables
`DATABASE_URL` (postgresql+psycopg://...?sslmode=require), `COMPANY_NAME`, `DEMO_PASSCODE` (simple shared gate for the public URL), `USE_LLM=false`, `SEED_ON_START=true|false`, `ALLOWED_ORIGINS`.

## Steps
1. Create a Neon (or Supabase) project; copy the pooled connection string into `.env`.
2. Run migrations and seed against it: `python -m backend.app.seed.seed --reset`.
3. Test locally: `docker compose up --build` then open http://localhost:8080.
4. **Ask the user for confirmation, GCP project id and region** (suggest `asia-south1`), then:
   `gcloud run deploy hr-agent-demo --source . --region <region> --allow-unauthenticated --set-env-vars DATABASE_URL=...,DEMO_PASSCODE=...,USE_LLM=false`
   (prefer Secret Manager for `DATABASE_URL` if the user wants it).
5. Hit `/api/health`, run the smoke test against the live URL, and return the URL.

## Fallback
Render: one Web Service from the same Dockerfile + Render Postgres or Neon.

Never run deploy commands without explicit user confirmation. Never commit `.env`.
''')

SKILLS["hr-test-verify"] = ("Use when writing or running tests and verification for the HR agent demo: agent smoke tests, router accuracy, API and frontend checks.", r'''
# Testing and verification

## Backend (pytest)
- `test_registry`: all 40 ids in `spec/agents.json` are registered; ids unique.
- `test_agents_smoke`: for each agent, run its `ask` as the right persona; assert valid Result shape, non-empty `summary`, no exception, audit row written.
- `test_stories`: planted stories exist (Jalandhar attrition rank 1, 37 data-quality issues, ATS lag, pay gap flagged, open case).
- `test_rbac`: employee cannot run Pay Equity; manager cannot see other teams; masking for n<5.
- `test_approvals`: Offer Letter Agent returns `pending_approval`; HR Head approval flips it to completed.
- `test_jarvis`: top-1 accuracy on the 40 `ask` strings >= 95% and top-3 = 100%; 20 paraphrases >= 80% top-1; low-confidence input returns a clarifying question.
- `test_api_e2e`: route -> confirm -> run -> audit visible.

## Frontend
- `npm run build` and `npm run typecheck` pass; no console errors on load.
- If Playwright is available: happy-path on a 390px viewport (route, confirm, result, approve).

## Report format
After testing print a table: check, status, details. List any agent that is only partially implemented. Never claim a check passed without running it.
''')

# ----------------------------------------------------------------------------
# 4. WORKFLOWS (slash commands)
# ----------------------------------------------------------------------------
WORKFLOWS = {}

WORKFLOWS["hr-status"] = ("Show build progress of the HR agent demo against spec/agents.json", r'''
1. Read `spec/agents.json`, `spec/PRD.md` and the repo tree.
2. List which stages exist: scaffold, database + seed, agent framework, employee-facing agents, people-infrastructure agents, Jarvis, API, portal, tests, deploy.
3. Count how many of the 40 agent ids are registered and passing their smoke test (run pytest if the backend exists).
4. Print a short status table and recommend the next slash command.
''')

WORKFLOWS["hr-build-all"] = ("Build the full HR agent demo end to end, stage by stage, with checkpoints", r'''
Use the `hr-stack-architecture` skill. Work in planning mode and keep a task list. After each stage: run its tests, summarise results and continue only if green.

1. Run `/hr-status` to see where we are.
2. Run `/hr-scaffold`.
3. Run `/hr-database`.
4. Run `/hr-framework`.
5. Run `/hr-agents-employee`.
6. Run `/hr-agents-infra`.
7. Run `/hr-jarvis`.
8. Run `/hr-api`.
9. Run `/hr-portal`.
10. Run `/hr-test` and fix failures until green.
11. Run `/hr-demo-script` to write the walkthrough.
12. Stop and ask the user whether to run `/hr-deploy`. Do not deploy without confirmation.
''')

WORKFLOWS["hr-scaffold"] = ("Create the repo structure, dependencies, env template and local run scripts", r'''
Load the `hr-stack-architecture` and `hr-cloud-deploy` skills.

1. Create the folder layout from the architecture skill (backend, frontend, spec stays as is).
2. Backend: `requirements.txt` (fastapi, uvicorn[standard], sqlalchemy>=2, psycopg[binary], pydantic>=2, pydantic-settings, faker, jinja2, scikit-learn, pytest, httpx), `__init__.py` files, `config.py`, `db.py`, `main.py` with `/api/health` and static-file serving with SPA fallback.
3. Frontend: `npm create vite@latest frontend -- --template react-ts`, add Tailwind, add Vite proxy `/api` -> `http://localhost:8000`.
4. Create `.env.example`, `.gitignore`, `docker-compose.yml` (api + local Postgres for dev), `Dockerfile` from the deploy skill, and a `Makefile` with `dev`, `seed`, `test`, `build`.
// turbo
5. Install dependencies and confirm `uvicorn backend.app.main:app` starts and `/api/health` returns ok.
6. Summarise what was created.
''')

WORKFLOWS["hr-database"] = ("Create the schema and the deterministic synthetic HR database with planted demo stories", r'''
Load the `hr-synthetic-data` skill.

1. Write SQLAlchemy models for every table in the skill and an init routine.
2. Write `seed/seed.py` with a fixed Faker seed, the volumes in the skill and `--reset` support.
3. Write `seed/stories.py` implementing all 8 planted stories exactly.
4. Seed policies, benefits, career ladder, panel availability and the integrations table with realistic content.
// turbo
5. Run the seed against local Postgres (or SQLite for dev) and print row counts per table.
6. Write tests that assert each planted story exists. Run them.
7. Ask the user for their Neon/Supabase connection string only if they want cloud now; otherwise continue locally.
''')

WORKFLOWS["hr-framework"] = ("Build the agent base class, registry, RBAC, audit and approval plumbing", r'''
Load the `hr-agent-framework` and `hr-governance-audit` skills.

1. Implement `agents/base.py`, `agents/registry.py` and the startup check that every id in `spec/agents.json` is registered.
2. Implement `governance/rbac.py`, `governance/audit.py` (`run_agent`) and `governance/approvals.py`.
3. Implement shared helpers: masking, persona scoping, Jinja2 template loader.
4. Create stub classes for all 40 agents that return a "not implemented" Result, so the registry check passes.
// turbo
5. Run the registry test and the RBAC tests.
''')

WORKFLOWS["hr-agents-employee"] = ("Implement the 20 employee-facing agents (Talent, Onboarding, Talent Mgmt & Dev, Business Partners)", r'''
Load the `hr-agent-framework` skill. Read the 20 agents with `layer = "Employee-facing"` in `spec/agents.json`, including each `logic` field.

1. Implement them group by group in `agents/employee_facing/` (talent.py, onboarding.py, talent_dev.py, business_partners.py).
2. For each agent write a pytest using its `ask` and assert against the planted stories where relevant (e.g. Team Health for Jalandhar).
3. Offer Letter Agent and Resume Screening Agent must create approvals.
// turbo
4. Run the tests and fix failures.
5. Report which agents are done.
''')

WORKFLOWS["hr-agents-infra"] = ("Implement the 20 people-infrastructure agents (People Ops, Total Rewards, People Analytics, HR Technology)", r'''
Load the `hr-agent-framework` and `hr-governance-audit` skills. Read the 20 agents with `layer = "People infrastructure"` in `spec/agents.json`.

1. Implement them group by group in `agents/people_infra/` (people_ops.py, total_rewards.py, people_analytics.py, hr_tech.py).
2. NL Query Agent: whitelist of parameterised query templates only, and show the SQL in the result.
3. Policy Q&A Agent: BM25 or TF-IDF over `policies`; cite clause, version, date.
4. Pay Equity, Attrition Risk, Investigation Doc, Case Triage and Sandbox agents are approval-required and decision-support only.
5. Agent Performance Monitor reads `audit_log`; make sure earlier agents have written rows.
// turbo
6. Run all tests and fix failures. Report which agents are done.
''')

WORKFLOWS["hr-jarvis"] = ("Build Jarvis, the central router that picks an agent and asks for confirmation", r'''
Load the `jarvis-router` skill.

1. Implement `jarvis/keywords.py` (hand-written keywords for all 40 agents), `jarvis/entities.py` and `jarvis/router.py`.
2. Expose `POST /api/jarvis/route` per the API contract. Include persona filtering and clarifying-question behaviour.
3. Add the optional LLM re-rank behind `USE_LLM`, default off and untested paths clearly marked.
// turbo
4. Run the router accuracy tests (top-1 >= 95% on all 40 asks, top-3 = 100%). Tune keywords until they pass.
5. Print a confusion list of any routing mistakes.
''')

WORKFLOWS["hr-api"] = ("Expose the REST API: agents, run, approvals, audit, dashboard, personas", r'''
Load the `hr-stack-architecture` and `hr-governance-audit` skills.

1. Implement every endpoint in the API contract with Pydantic models and persona header handling.
2. `POST /api/agents/{id}/run` must reject unconfirmed runs, enforce RBAC, log audit and handle approvals.
3. Implement `/api/dashboard/summary` from real DB aggregates (headcount, attrition by branch, open reqs, agent usage, integration health).
4. Add optional `DEMO_PASSCODE` gate via a simple header or cookie.
// turbo
5. Run the API e2e test (route -> confirm -> run -> audit) and fix failures.
''')

WORKFLOWS["hr-portal"] = ("Build the React portal: Jarvis chat with confirm card, catalog, approvals, audit, dashboard", r'''
Load the `hr-portal-frontend` skill (and the `frontend-design` skill if available).

1. Write the typed API client from the contract.
2. Build the five pages in the skill with a persona switcher and a Synthetic-data banner.
3. Catalog page must mirror the slide's 5 layers and 8 agent groups using `/api/agents`.
4. Make it work at 390px width first, then desktop.
// turbo
5. Run `npm run build` and typecheck. Start backend and frontend together and verify the golden path in the browser: route -> confirm -> result -> switch persona -> approve -> audit.
6. Take screenshots of each page and summarise any UI issues; fix them.
''')

WORKFLOWS["hr-test"] = ("Run all verification and print a pass/fail report", r'''
Load the `hr-test-verify` skill.

// turbo
1. Run the full backend test suite.
2. Run frontend build and typecheck.
3. Run the end-to-end flow (and the Playwright mobile test if available).
4. Print the report table. List anything failing or partially implemented and fix it, then re-run.
''')

WORKFLOWS["hr-deploy"] = ("Containerise and deploy the demo to the cloud (asks for confirmation first)", r'''
Load the `hr-cloud-deploy` skill. Do NOT run any deploy command until the user confirms each of the following.

1. Ask which database to use (Neon or Supabase) and request the connection string. Never print it back or commit it.
2. Seed the cloud database.
3. Build the Docker image locally and run it with `docker compose up --build`; check `/api/health`.
4. Ask for the GCP project id and region, and whether to use Cloud Run (default) or Render.
5. Deploy, set env vars (`DATABASE_URL`, `DEMO_PASSCODE`, `COMPANY_NAME`, `USE_LLM=false`).
6. Run a smoke test against the live URL and return the URL plus the demo passcode.
''')

WORKFLOWS["hr-add-agent"] = ("Add or modify a single agent and keep spec, code, router and tests in sync", r'''
Load the `hr-agent-framework` and `jarvis-router` skills.

1. Ask the user for the agent name, group, a sample ask and what it should do.
2. Add it to `spec/agents.json` (unique id from the name) and to `jarvis/keywords.py`.
3. Implement the class, a template if needed and a pytest.
// turbo
4. Run router and agent tests. Confirm the new ask routes top-1 to the new agent.
''')

WORKFLOWS["hr-demo-script"] = ("Write a 5-minute CHRO walkthrough script and talking points for the live demo", r'''
1. Read `spec/PRD.md` and run the app to confirm the planted stories still hold.
2. Write `docs/DEMO_SCRIPT.md`: a 5-minute walkthrough for a CHRO with exact prompts to type, the persona to use, what the audience should notice, and a 1-line "so what" per step.
3. Include a screenshot checklist and a "what to say if asked" list: why no LLM inside the agents, how data privacy works, how this would connect to a real HRIS, what a pilot would look like.
4. Keep it under two pages.
''')

# ----------------------------------------------------------------------------
# 5. PRD + README
# ----------------------------------------------------------------------------
PRD = r'''# PRD: HR Agent Stack demo

**Audience:** CHRO and HR leadership. **Goal:** make the "40 AI Agents Transforming Modern HR" slide tangible in a working, cloud-hosted portal.

## Scope
- Synthetic Postgres database (~600 employees) with planted demo stories.
- 40 deterministic agents (see `agents.json`), organised exactly as the slide: employee-facing (Talent, Onboarding, Talent Mgmt & Dev, Business Partners) and people infrastructure (People Ops, Total Rewards, People Analytics, HR Technology).
- Central **Jarvis** router: interprets a message, proposes an agent, user confirms on the page, agent runs.
- Governance: personas, RBAC, audit log, approvals, privacy masking.
- Web portal (mobile-first) and a public cloud URL protected by a demo passcode.

## Non-goals
Real HRIS integration, real employee data, production auth, LLM-driven agents.

## Demo storyline (5 minutes)
1. **Jarvis routes:** "Which branches are at risk of attrition?" -> confirm card -> Attrition Risk Agent -> Jalandhar tops the list. Approval-required, shows decision-support note.
2. **Governed action:** as Recruiter, "Draft an offer for the selected candidate" -> pending approval. Switch to HR Head -> approve -> audit trail updates.
3. **Employee self-service:** as Priya, "How many casual leaves do I get?" -> policy clause with version. "Explain my ESOP vesting."
4. **Insight:** as Total Rewards Lead, "Check pay gaps in the RM cohort" -> outlier flagged, small groups masked.
5. **Trust:** open Audit page: every action logged. Open Catalog: the slide, now clickable.

## Success criteria
All 40 agents run and are audited; Jarvis top-1 >= 95% on sample asks; golden path works on a phone; deployed URL stable; no real PII anywhere.
'''

README = r'''# HR Agent Stack: Antigravity build kit

Generated by `setup_hr_agents_antigravity.py`.

## Use it
1. Open this folder in **Google Antigravity** as the workspace.
2. Start the agent panel in planning mode.
3. Type `/hr-status`, then `/hr-build-all` and review at each checkpoint.
   Or run stages yourself, in order:
   `/hr-scaffold` -> `/hr-database` -> `/hr-framework` -> `/hr-agents-employee` -> `/hr-agents-infra` -> `/hr-jarvis` -> `/hr-api` -> `/hr-portal` -> `/hr-test` -> `/hr-demo-script` -> `/hr-deploy`
4. Helpers: `/hr-add-agent`, `/hr-status`.

## What is in here
- `.agent/rules/`: always-on project rules
- `.agent/skills/`: 8 skills the agent loads per stage
- `.agent/workflows/`: the slash commands
- `spec/`: agents.json (40 agents), personas.json, layers.json, PRD.md, agents.md

If slash commands do not show up, your Antigravity version may use `.agents/` instead of `.agent/`.
Re-run the generator with `--both`.
'''


# ----------------------------------------------------------------------------
# 5b. V2 ADDITIONS: Google Stitch UI pipeline, Gemini guardrails (model proposes,
#     code decides), hackathon scorecard, PERT/CPM sprint planner, pitch kit
# ----------------------------------------------------------------------------
_old = "Jarvis may use an optional LLM only behind `USE_LLM=true` (default `false`). The demo must work with no API key."
assert _old in RULE
RULE = RULE.replace(_old, "Gemini may be used by Jarvis only as a *proposer* (see rule 9) behind `USE_LLM=true`; the demo must still work with no API key.")
RULE += r'''
## Hackathon mode (Google x Hack2skill style)
9. **Model proposes, pure code decides.** Gemini only suggests a route or phrasing. The registry, RBAC, parameter validation and every number shown to the user come from code. Every model output is schema-validated and allowlist-checked.
10. **Graceful degradation.** If Gemini or the network fails, Jarvis falls back to the deterministic router. The demo must also work offline (`OFFLINE_DEMO=true` serves cached golden responses).
11. **Judged axes:** Code Quality, Security, Efficiency, Testing, Accessibility, Problem Statement Alignment. Work to `spec/SCORECARD.md`; run `/hr-quality-gate` before every demo or submission.
12. **UI comes from Stitch.** Design with the Stitch MCP and skills (`/hr-design`). `.stitch/DESIGN.md` is the design source of truth. If Stitch is unavailable, follow `spec/DESIGN_BRIEF.md` by hand. Never ship a generic template look.
13. **Plan with numbers.** Use `python tools/pert.py` (PERT/CPM on `spec/plan.json`) to plan and replan. Protect the critical path; cut scope by MoSCoW, never by dropping tests, security or accessibility.
14. **Time box.** Reserve the last 15% of the time for deploy, the demo-safe cache and the pitch.
15. **Traceability.** Paste the official problem statement into `/hr-align` first; every feature must map to a requirement and a test.
'''

PLAN = [
    {"id": "T1", "name": "Scaffold repo, deps, env", "o": 0.3, "m": 0.5, "p": 1.0, "deps": [], "priority": "must", "cmd": "/hr-scaffold"},
    {"id": "T2", "name": "Stitch setup + DESIGN.md", "o": 0.3, "m": 0.5, "p": 1.0, "deps": [], "priority": "must", "cmd": "/hr-stitch-setup"},
    {"id": "T3", "name": "Database + seed + planted stories", "o": 0.5, "m": 0.8, "p": 1.5, "deps": ["T1"], "priority": "must", "cmd": "/hr-database"},
    {"id": "T4", "name": "Agent framework, RBAC, audit, approvals", "o": 0.4, "m": 0.7, "p": 1.2, "deps": ["T1", "T3"], "priority": "must", "cmd": "/hr-framework"},
    {"id": "T5", "name": "20 employee-facing agents", "o": 0.8, "m": 1.2, "p": 2.0, "deps": ["T4"], "priority": "must", "cmd": "/hr-agents-employee"},
    {"id": "T6", "name": "20 people-infrastructure agents", "o": 0.8, "m": 1.2, "p": 2.0, "deps": ["T4"], "priority": "must", "cmd": "/hr-agents-infra"},
    {"id": "T7", "name": "Jarvis deterministic router", "o": 0.4, "m": 0.6, "p": 1.0, "deps": ["T4"], "priority": "must", "cmd": "/hr-jarvis"},
    {"id": "T8", "name": "Gemini layer + guardrails + evals", "o": 0.5, "m": 0.8, "p": 1.5, "deps": ["T7"], "priority": "should", "cmd": "/hr-gemini"},
    {"id": "T9", "name": "REST API", "o": 0.4, "m": 0.6, "p": 1.0, "deps": ["T5", "T6", "T7"], "priority": "must", "cmd": "/hr-api"},
    {"id": "T10", "name": "Stitch screens (mobile + desktop)", "o": 0.5, "m": 0.8, "p": 1.5, "deps": ["T2"], "priority": "must", "cmd": "/hr-design"},
    {"id": "T11", "name": "Portal built from Stitch design", "o": 0.8, "m": 1.2, "p": 2.0, "deps": ["T9", "T10"], "priority": "must", "cmd": "/hr-portal"},
    {"id": "T12", "name": "Quality gate: security, a11y, tests, efficiency", "o": 0.5, "m": 0.8, "p": 1.5, "deps": ["T11"], "priority": "must", "cmd": "/hr-quality-gate"},
    {"id": "T13", "name": "Scale, govern, optimise pass", "o": 0.4, "m": 0.6, "p": 1.0, "deps": ["T12", "T8"], "priority": "could", "cmd": "/hr-govern-scale"},
    {"id": "T14", "name": "Deploy to Cloud Run", "o": 0.3, "m": 0.5, "p": 1.0, "deps": ["T12"], "priority": "must", "cmd": "/hr-deploy"},
    {"id": "T15", "name": "Pitch, README, demo-safe cache", "o": 0.5, "m": 0.7, "p": 1.0, "deps": ["T14"], "priority": "must", "cmd": "/hr-pitch"},
]

PERT_PY = r'''#!/usr/bin/env python3
"""PERT/CPM planner for the hackathon sprint (stdlib only).

  python tools/pert.py --hours 6
  python tools/pert.py --hours 6 --elapsed 1.5 --done T1,T2,T3
  python tools/pert.py --hours 6 --serial        # one builder, no parallel agents

Reads spec/plan.json. Expected time te = (o + 4m + p) / 6, variance ((p - o) / 6)^2.
Prints the critical path, slack, probability of finishing inside the budget, and
MoSCoW-based scope cuts if the probability is below --target.
"""
import argparse
import json
import math
from pathlib import Path


def te(t):
    return (t["o"] + 4 * t["m"] + t["p"]) / 6


def var(t):
    return ((t["p"] - t["o"]) / 6) ** 2


def topo(by):
    order, seen, temp = [], set(), set()

    def visit(i):
        if i in seen:
            return
        if i in temp:
            raise SystemExit(f"dependency cycle at {i}")
        temp.add(i)
        for d in by[i]["deps"]:
            visit(d)
        temp.discard(i)
        seen.add(i)
        order.append(i)

    for i in by:
        visit(i)
    return order


def analyse(tasks, done, serial):
    by = {t["id"]: t for t in tasks}
    order = topo(by)
    dur = {i: 0.0 if i in done else te(by[i]) for i in order}
    vr = {i: 0.0 if i in done else var(by[i]) for i in order}
    if serial:
        return dict(by=by, order=order, dur=dur, es={}, slack={}, crit=[i for i in order if dur[i] > 0],
                    end=sum(dur.values()), sd=math.sqrt(sum(vr.values())))
    es, ef = {}, {}
    for i in order:
        es[i] = max([ef[d] for d in by[i]["deps"] if d in ef] or [0.0])
        ef[i] = es[i] + dur[i]
    end = max(ef.values()) if ef else 0.0
    succ = {i: [] for i in by}
    for i in by:
        for d in by[i]["deps"]:
            if d in succ:
                succ[d].append(i)
    ls, lf = {}, {}
    for i in reversed(order):
        lf[i] = min([ls[s] for s in succ[i]] or [end])
        ls[i] = lf[i] - dur[i]
    slack = {i: max(0.0, round(ls[i] - es[i], 4)) for i in by}
    crit = [i for i in order if dur[i] > 0 and slack[i] < 1e-9]
    groups = {}
    for i in crit:
        key = round(es[i], 6)
        groups[key] = max(groups.get(key, 0.0), vr[i])
    sd = math.sqrt(sum(groups.values()))
    return dict(by=by, order=order, dur=dur, es=es, slack=slack, crit=crit, end=end, sd=sd)


def prob(budget, end, sd):
    if sd == 0:
        return 1.0 if budget >= end else 0.0
    return 0.5 * (1 + math.erf((budget - end) / (sd * math.sqrt(2))))


def required(by, ids, done):
    req, stack = set(), [i for i in ids if by[i].get("priority", "must") == "must"]
    while stack:
        i = stack.pop()
        if i in req:
            continue
        req.add(i)
        stack.extend(d for d in by[i]["deps"] if d not in done)
    return req


def dependents(tasks, root):
    cut, grew = {root}, True
    while grew:
        grew = False
        for t in tasks:
            if t["id"] not in cut and any(d in cut for d in t["deps"]):
                cut.add(t["id"])
                grew = True
    return cut


def suggest_cuts(tasks, done, budget, serial, target):
    """Greedy MoSCoW cuts that actually shorten the schedule; never touches must-tasks or their deps."""
    cut = set()
    while True:
        active = [t for t in tasks if t["id"] not in cut]
        r = analyse(active, done, serial)
        if prob(budget, r["end"], r["sd"]) >= target:
            break
        ids = [t["id"] for t in active if t["id"] not in done]
        req = required(r["by"], ids, done)
        best = None
        for i in (x for x in ids if x not in req):
            closure = dependents(active, i)
            r2 = analyse([t for t in active if t["id"] not in closure], done, serial)
            gain = r["end"] - r2["end"]
            if gain > 1e-9:
                rank = {"could": 0, "should": 1}.get(r["by"][i].get("priority"), 2)
                key = (rank, -gain)
                if best is None or key < best[0]:
                    best = (key, closure)
        if best is None:
            break
        cut |= best[1]
    return sorted(cut)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="spec/plan.json")
    ap.add_argument("--hours", type=float, default=6.0, help="total hackathon hours")
    ap.add_argument("--elapsed", type=float, default=0.0)
    ap.add_argument("--done", default="")
    ap.add_argument("--serial", action="store_true")
    ap.add_argument("--target", type=float, default=0.8)
    a = ap.parse_args()

    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    tasks = plan["tasks"]
    done = {x.strip() for x in a.done.split(",") if x.strip()}
    reserve = plan.get("reserve_pct", 0.15)
    budget = (a.hours - a.elapsed) * (1 - reserve)
    r = analyse(tasks, done, a.serial)
    p = prob(budget, r["end"], r["sd"])

    print(f"Mode: {'serial (1 builder)' if a.serial else 'parallel agents'} | budget {budget:.2f}h "
          f"(after {int(reserve * 100)}% reserve) | expected {r['end']:.2f}h | sd {r['sd']:.2f}h")
    print(f"P(finish in budget) = {p * 100:.0f}%\n")
    print(f"{'id':4} {'task':46} {'te(h)':>6} {'slack':>6}  prio    status")
    for i in r["order"]:
        t = r["by"][i]
        status = "done" if i in done else ("CRITICAL" if i in r["crit"] else "")
        print(f"{i:4} {t['name'][:46]:46} {r['dur'][i]:6.2f} {r['slack'].get(i, 0):6.2f}  {t.get('priority', 'must'):7} {status}")
    if a.serial:
        print("\nCritical path:", " -> ".join(r["crit"]) or "none")
    else:
        steps = {}
        for i in r["crit"]:
            steps.setdefault(round(r["es"].get(i, 0), 6), []).append(i)
        print("\nCritical path (+ = runs in parallel):",
              " -> ".join(" + ".join(v) for _, v in sorted(steps.items())) or "none")
    if p < a.target:
        cuts = suggest_cuts(tasks, done, budget, a.serial, a.target)
        r2 = analyse([t for t in tasks if t["id"] not in set(cuts)], done, a.serial)
        p2 = prob(budget, r2["end"], r2["sd"])
        if cuts:
            names = ", ".join(f"{i} ({r['by'][i]['name']})" for i in cuts)
            print(f"\nBelow {int(a.target * 100)}% confidence. Suggested MoSCoW cuts: {names} -> P becomes {p2 * 100:.0f}%")
        else:
            print(f"\nBelow {int(a.target * 100)}% confidence and no cut shortens the schedule (the must-have path is the bottleneck).")
        if p2 < a.target:
            need = r2["end"] / (1 - reserve) + a.elapsed
            print(f"Still below target: the must-have path needs about {need:.1f}h in total. "
                  "Add hours or parallel agents, or shrink the must-tasks (never tests, security or accessibility).")
    else:
        print(f"\nOn track (>= {int(a.target * 100)}%). Start every critical task first; run slack tasks in parallel.")


if __name__ == "__main__":
    main()
'''

MCP_OFFICIAL = '''{
  "mcpServers": {
    "stitch": {
      "serverUrl": "https://stitch.googleapis.com/mcp",
      "headers": { "X-Goog-Api-Key": "PASTE_YOUR_OWN_STITCH_API_KEY_HERE" }
    }
  }
}
'''
MCP_PROXY = '''{
  "mcpServers": {
    "stitch": {
      "command": "npx",
      "args": ["@_davideast/stitch-mcp", "proxy"]
    }
  }
}
'''

STITCH_SETUP = r'''# Stitch MCP setup (5 minutes)

1. Get a Stitch API key from Stitch settings (stitch.withgoogle.com). Keep it private: never paste it into chat, code or git.
2. In Antigravity: agent panel menu -> **MCP servers** -> **Manage MCP servers** -> view raw config.
3. Paste `tools/mcp/stitch.official.example.json` and replace the placeholder with your key.
   If that format is rejected by your version, try `tools/mcp/stitch.proxy.example.json` (a community proxy, `@_davideast/stitch-mcp`) and follow its auth prompt.
4. Install the official skills:
   ```
   npx skills add google-labs-code/stitch-skills --list
   npx skills add google-labs-code/stitch-skills --skill stitch-design
   npx skills add google-labs-code/stitch-skills --skill design-md
   npx skills add google-labs-code/stitch-skills --skill enhance-prompt
   npx skills add google-labs-code/stitch-skills --skill react:components
   ```
   Use the exact names printed by `--list` (the React skill may appear as `react-components`). Optional: `stitch-loop`, `shadcn-ui`, `taste-design`, `remotion`.
5. In the agent panel run `/hr-stitch-setup` to verify, then `/hr-design`.

No Stitch access? Skip it. `/hr-design` has a fallback that builds from `spec/DESIGN_BRIEF.md`. You can also export a Stitch project as a zip (HTML, images, design.md) and drop it in `.stitch/`.
Configuration formats change; if a step fails, check the current Stitch MCP docs.
'''

DESIGN_BRIEF = r'''# Design brief: HR Agent Stack portal

**Feel:** calm, credible, human. A people-leadership product for a CHRO, not a developer tool. Warm and editorial, with precise data.

## Tokens (starting point; Stitch may refine, keep contrast >= 4.5:1)
- Background warm off-white `#F7F5F0`, surface `#FFFFFF`, ink `#17211F`, muted `#5B6764`, border `#E2DED4`
- Primary deep teal `#0F5C55`; attention/approvals amber `#B26A00`; success `#2E7D4F`; danger `#B3372F`
- Five layer tints (quiet): Strategic sand, Orchestration sage, Employee-facing teal-mist, People infrastructure slate-mist, Foundation stone
- Dark mode supported (same hues, lower luminance)
- Type: editorial serif for headings (Newsreader or Fraunces), humanist sans for UI (IBM Plex Sans or Geist), tabular numerals for data
- Radius 12px cards, 8px controls; soft 1px borders over heavy shadows; 8px spacing grid
- Icons: line icons (Lucide). No emoji as icons.

## Avoid
Purple/neon gradients, heavy glassmorphism, stock illustrations, "Inter + blue button" template look, dense dashboards with no hierarchy, colour-only status.

## Screens (design each at 390px and 1440px)
1. **Jarvis home:** conversation + suggested prompts (from agents' `ask`). Hero component is the **confirm card**: agent chip with layer colour, editable parameter chips, Confirm (primary) / Change agent / Cancel, plus a trust line ("Logged, decision support, human approves"). Result card below: summary sentence first, then table/checklist/doc, "SQL used" expander, approval badge.
2. **Agent catalog:** the original slide made interactive. Five layers, eight groups, 40 chips. Tap opens a drawer (what it does, tools, data scope, approval rule, sample ask, Try it).
3. **Approvals:** queue with who/what/why, Approve and Reject with note, status timeline.
4. **Audit & trust:** filterable log, expandable row with params and outcome.
5. **CHRO dashboard:** headcount, attrition by branch (Jalandhar stands out), open requisitions, agent usage, integration health. Few numbers, large, each with a one-line "so what".
6. **Persona switcher + Synthetic-data banner** present on every screen.

## Behaviour
Mobile: bottom navigation, single column. Desktop: two panes (conversation left, context right). Motion 150 to 250ms, honours `prefers-reduced-motion`. Voice: plain, short, human. States for loading, empty, error, pending approval.
'''

SCORECARD = r'''# Scorecard: what the judges score, and how we prove it

Target: >= 95 on every axis. Run `/hr-quality-gate` to produce this table with real command output.

| Axis | Target | Gates (run, do not assume) |
|---|---|---|
| **Code Quality** | clean, small, typed, consistent | `ruff check`, `ruff format --check`, `mypy` (strict on `agents/`, `jarvis/`, `governance/`), `eslint`, `tsc --noEmit`; functions <= 40 lines, cyclomatic complexity <= 10, no dead code, docstrings on public functions, one responsibility per module, clear naming, no copy-paste agents (shared helpers) |
| **Security** | no secrets, safe inputs, safe outputs | `bandit -r backend`, `pip-audit`, `npm audit --omit=dev`; parameterised SQL only; Pydantic validation on every request; CORS allowlist; security headers (CSP, X-Content-Type-Options, frame-ancestors); rate limiting; secrets only via env/Secret Manager; RBAC on every run; audit append-only; prompt-injection tests; no PII in logs |
| **Efficiency** | fast and lean | indexes on filter columns, no N+1 (test query counts), response cache for hot read-only agents, pagination, gzip, frontend initial JS <= 250 KB gzip, code-split pages, p95 API latency < 300 ms (excluding Gemini), Gemini calls cached and time-limited |
| **Testing** | broad, meaningful, automated | `pytest --cov=backend --cov-fail-under=85`; 40 agent smoke tests; RBAC, approvals, masking, router accuracy (top-1 >= 95%), planted stories, API e2e, offline-demo test; frontend unit tests (vitest) and one Playwright mobile happy path |
| **Accessibility** | WCAG 2.2 AA | `@axe-core/playwright` zero serious/critical violations on every page; keyboard-only path through Jarvis confirm flow; `aria-live` on chat results; contrast >= 4.5:1; targets >= 44px; reduced-motion; semantic landmarks; Lighthouse a11y >= 95 |
| **Problem Statement Alignment** | every requirement traced | `docs/TRACEABILITY.md`: requirement -> agent/feature -> test -> demo step. Nothing in the demo that is not tied to a requirement; nothing required that is missing |

## Differentiators beyond the rubric (from mentor feedback)
Guardrails and grounding (see `gemini-guardrails`), prompt and agent versioning, an eval harness with history, and a scale/govern/optimise pass (`/hr-govern-scale`). Put these in the pitch.
'''

SKILLS["stitch-design-pipeline"] = ("Use when designing or building any UI. Covers Google Stitch MCP setup, the official Stitch skills, DESIGN.md as the design source of truth, converting Stitch screens to React, and the accessibility fixes generated markup needs.", r'''
# Stitch design pipeline (clean, modern UI)

Goal: a distinctive, calm, credible interface designed in Google Stitch and handed to code through the Stitch MCP and the official Stitch skills. Domain-agnostic: reuse for any hackathon UI.

## One-time setup (`/hr-stitch-setup`)
1. Skills (run `--list` first and use the exact names it prints; install together because they depend on each other):
   `npx skills add google-labs-code/stitch-skills --list`
   `--skill stitch-design`, `--skill design-md`, `--skill enhance-prompt`, `--skill react:components` (may be `react-components`).
   Optional: `stitch-loop` (multi-page), `shadcn-ui`, `taste-design` (anti-generic rules), `remotion` (walkthrough video).
2. MCP: Antigravity agent panel menu -> MCP servers -> Manage -> raw config; paste `tools/mcp/stitch.official.example.json` with the user's own key. The key lives only in that config or an env var. Never ask the user to paste it into chat and never commit it.
3. Verify by listing Stitch projects. If it fails, try the proxy example, then use the fallback below.

## Pipeline
1. Read `spec/DESIGN_BRIEF.md`. Run `enhance-prompt` to produce one Stitch-optimised prompt per screen.
2. `stitch-design`: create project "HR Agent Stack"; generate each screen at 390px and 1440px; two variants for Jarvis home; pick one and say why.
3. `design-md`: write `.stitch/DESIGN.md` (colours, type, spacing, radii, components, do and don't). Commit it.
4. `react:components`: convert screens to React components in `frontend/src/components`, mapping DESIGN.md tokens to Tailwind theme and CSS variables. Wire real API data. Keep all states: loading, empty, error, pending approval.
5. Run the accessibility fixes below, then `/hr-quality-gate`.

## Fallback (no Stitch access)
Write `.stitch/DESIGN.md` by hand from the brief, build with Tailwind and shadcn/ui using the same tokens, and state in the report that Stitch was unavailable.

## Fixes generated markup usually needs
Landmarks (header, nav, main), one h1 per page, labelled inputs, `aria-live="polite"` on chat and results, focus moves to the result after Confirm, visible focus rings, contrast >= 4.5:1, targets >= 44px, `prefers-reduced-motion`, table captions and scroll containers, status never by colour alone.
''')

SKILLS["gemini-guardrails"] = ("Use when adding Gemini (and optionally Google ADK) to Jarvis: proposal-only routing, structured output, grounding, input and output guardrails, prompt and agent versioning, evals and graceful fallback.", r'''
# Gemini layer: the model proposes, pure code decides

## Principle
Gemini never executes anything and never produces numbers shown to the user. It proposes `{agent_id, params, confidence, rationale}`. Code validates, checks RBAC, asks the user to confirm, runs a deterministic agent, and renders the result. Domain-agnostic pattern.

## Build
- SDK: `google-genai`. Model name from `GEMINI_MODEL` (check current model names in the Gemini docs before coding; default to a current Flash-tier model). Key from `GEMINI_API_KEY` via env or Secret Manager, never in code.
- **Structured output:** request JSON matching a Pydantic schema; parse with Pydantic; reject anything else.
- **Allowlist:** `agent_id` must exist in `spec/agents.json` and be allowed for the persona; params must pass per-agent validators. Otherwise ignore the proposal.
- **Merge:** compare with the deterministic router. If they agree, raise confidence; if they disagree, show both in the confirm card.
- **Grounded narration (optional):** Gemini may rewrite an agent's result in friendly words, but only from the result JSON. A validator checks that every number and name in the narration appears in the result; if not, show the template summary instead.
- **Context minimisation:** the model sees the agent catalogue (names, asks) and the user message, never raw rows or PII.
- **Input guardrails:** max length, strip control characters, injection patterns ("ignore previous", "reveal system prompt", SQL fragments), PII redaction (Aadhaar, PAN, phone, email) before the model sees text.
- **Output guardrails:** schema check, allowlist, refusal path for out-of-scope or unsafe requests ("I can help with HR questions in these areas..."), never reveal prompts.
- **Resilience:** timeout (4 s), one retry, circuit breaker; on failure fall back to the deterministic router and note it in the audit row. `OFFLINE_DEMO=true` serves cached golden responses.
- **Versioning:** prompts in `backend/app/jarvis/prompts/jarvis.v1.md`; `PROMPT_VERSION`, `MODEL`, agent `version` written to every audit row. Changing a prompt means a new file and an eval run.
- **Optional Google ADK path (stretch, only when everything else is green):** model Jarvis as an ADK root agent with the eight groups as sub-agents and a single `propose_route` tool that records a proposal and never executes. Check the current ADK docs before coding; if there is friction, keep the plain SDK.

## Evals (`evals/`)
`golden.seed.jsonl` already holds the 40 sample asks. Extend to >= 100: paraphrases, multi-entity asks, 15 prompt-injection attempts, 10 out-of-scope requests, 10 RBAC denials. `make eval` prints: route accuracy (top-1, top-3), parameter extraction accuracy, groundedness (narration numbers found in result), refusal correctness, injection resistance, p50/p95 latency, token cost. Save each run to `evals/results/<timestamp>.json`. Gates: accuracy >= 95%, groundedness 100%, injection resistance 100%.
''')

SKILLS["hack-quality-gates"] = ("Use before any demo or submission, and whenever code is added: run the judged-axis gates (code quality, security, efficiency, testing, accessibility, problem alignment) and produce a scorecard with real evidence.", r'''
# Hackathon quality gates

Read `spec/SCORECARD.md`. For each axis run the listed commands (install tools into a virtualenv or dev dependencies first; if a tool is unavailable, say so rather than guessing).

## Procedure
1. Run every gate and capture the real output.
2. Fix failures in this order: Security, Testing, Accessibility, Code Quality, Efficiency, Alignment.
3. Re-run until green or until two rounds have passed.
4. Print the scorecard table: axis, status, evidence (command and result), estimated score band, top deduction, fix applied.
5. Never claim a gate passed without running it. Never lower a threshold to pass.

## Security checklist
No secrets in repo or logs; parameterised SQL; request validation; CORS allowlist; CSP and security headers; rate limit on `/api/jarvis/route` and run endpoints; RBAC on every run; audit append-only; prompt-injection and PII tests; dependency audit clean or documented; demo passcode enabled on the public URL; synthetic-data banner present.

## Accessibility checklist
Axe clean on every page at 390px and 1440px; keyboard-only completion of route, confirm, result, approve; `aria-live` regions; focus order; contrast; reduced motion; labels and landmarks; zoom to 200% without loss.

## Efficiency checklist
Query counts per request, indexes, caching, pagination, bundle size, lazy loading, p95 latency, cold-start check on Cloud Run.
''')

SKILLS["hack-pert-planner"] = ("Use when planning or replanning a time-boxed hackathon build: PERT/CPM estimates, critical path, probability of finishing, MoSCoW scope cuts and dynamic replanning.", r'''
# PERT/CPM sprint planner

Files: `spec/plan.json` (tasks with o/m/p hours, deps, priority must|should|could, workflow command) and `tools/pert.py`.

## Use
- Plan: `python tools/pert.py --hours <total>` (parallel agents) or add `--serial` for one builder. Reserve 15% is applied automatically.
- Replan after each task: `python tools/pert.py --hours <total> --elapsed <used> --done T1,T2,...`.
- Read the output: critical path (start these first), slack (run in parallel), P(finish) and suggested MoSCoW cuts.

## Rules
- If P(finish) < 80%: apply the suggested cuts in `spec/plan.json` (set `priority: "cut"` and note it in `docs/PLAN_STATUS.md`), never cut tests, security or accessibility.
- If a task overruns its pessimistic estimate, stop, re-estimate the remaining tasks and say what changed.
- Conditions change the plan: fewer hours, a failing integration, no Stitch access, no Gemini key. Update `plan.json` and replan rather than pushing on.
- Keep `docs/PLAN_STATUS.md` current: done, in progress, next, cuts, risks.
''')

SKILLS["hack-pitch-submission"] = ("Use when preparing the demo, pitch, README, architecture diagram, social post and final submission checklist for a hackathon.", r'''
# Pitch and submission kit

## 3-minute pitch (structure)
1. Problem and why it matters (20 s). 2. Insight: one governed brain (Jarvis) routing to 40 specialised agents (20 s). 3. Live demo, 4 steps (90 s): route and confirm, governed action with approval, employee self-service, audit trail. 4. Architecture in one picture (20 s): model proposes, code decides. 5. Trust and scale: guardrails, versioning, evals, Cloud Run (20 s). 6. Ask and next step (10 s).

## Deliverables
- `README.md`: problem, solution, screenshots, architecture (Mermaid), how to run, how it maps to each judged axis, test and eval results, limitations.
- `docs/ARCHITECTURE.md` with a Mermaid diagram of the five layers and the request flow.
- `docs/TRACEABILITY.md` and `docs/DEMO_SCRIPT.md`.
- Demo-safe cache: record golden responses for the demo prompts into `backend/app/demo_cache.json`, served when `OFFLINE_DEMO=true`. Rehearse once with the network off.
- Optional walkthrough video using the Stitch `remotion` skill.
- Social post drafts (3 variants: results-led, story-led, learning-led) in `docs/SOCIAL.md`.

## Final checklist
Public URL works on a phone; passcode noted; synthetic-data banner visible; no secrets in repo; scorecard table pasted in README; test, eval and axe outputs saved under `docs/evidence/`; demo rehearsed twice; backup screen recording saved.
''')

SKILLS["hr-cloud-deploy"] = (SKILLS["hr-cloud-deploy"][0], SKILLS["hr-cloud-deploy"][1].replace(
    "`USE_LLM=false`, `SEED_ON_START=true|false`, `ALLOWED_ORIGINS`.",
    "`USE_LLM=true|false`, `GEMINI_MODEL`, `SEED_ON_START=true|false`, `ALLOWED_ORIGINS`, `OFFLINE_DEMO=false`. Store `GEMINI_API_KEY` and `DATABASE_URL` in Secret Manager and mount them (`--set-secrets`); never pass keys as plain command-line literals."))

SKILLS["hr-portal-frontend"] = (SKILLS["hr-portal-frontend"][0], SKILLS["hr-portal-frontend"][1].replace(
    "If a `frontend-design` skill is available, load it and make deliberate, non-generic design choices suited to an HR/people product for a CHRO audience. Calm, credible, readable. No default template look.",
    "Design comes from Stitch: load the `stitch-design-pipeline` skill and build from `.stitch/DESIGN.md` and the Stitch screens. Follow `spec/DESIGN_BRIEF.md`. Calm, credible, readable, never a default template look."))

SKILLS["jarvis-router"] = (SKILLS["jarvis-router"][0], SKILLS["jarvis-router"][1].replace(
    "- Optional: if `USE_LLM=true` and an API key exists, use an LLM only to re-rank the top 3. Default off.",
    "- Gemini is an optional *proposer* layered on top (see the `gemini-guardrails` skill, `/hr-gemini`). The deterministic router stays as validator and fallback."))

WORKFLOWS["hr-stitch-setup"] = ("Install the official Stitch skills, connect the Stitch MCP server, and verify the design pipeline", r'''
Load the `stitch-design-pipeline` skill. Never ask the user to paste an API key into chat.

// turbo
1. Run `npx skills add google-labs-code/stitch-skills --list` and show the available skills.
2. Install `stitch-design`, `design-md`, `enhance-prompt` and the React skill (use the exact names listed). Ask before installing optional ones (`stitch-loop`, `shadcn-ui`, `taste-design`, `remotion`).
3. Show `tools/mcp/stitch.official.example.json` and `STITCH_SETUP.md`. Ask the user to add the server in the MCP servers panel with their own key, then reply "done".
4. Verify by listing Stitch projects through the MCP. If it fails, offer the proxy example. If it still fails, write "Stitch unavailable, using fallback" in `docs/DECISIONS.md` and continue.
''')

WORKFLOWS["hr-design"] = ("Design the portal in Google Stitch (or the fallback), produce DESIGN.md and screens", r'''
Load the `stitch-design-pipeline` skill and read `spec/DESIGN_BRIEF.md`.

1. Run `enhance-prompt` for each of the 6 screens in the brief.
2. With the Stitch MCP, create the project "HR Agent Stack" and generate each screen at 390px and 1440px. Generate two variants of Jarvis home and choose one with a one-line reason.
3. Run `design-md` and save `.stitch/DESIGN.md`. Save screen HTML to `.stitch/screens/`.
4. List the screens created and the token summary (colours, type, radius).
5. If Stitch is unavailable, write `.stitch/DESIGN.md` by hand from the brief and say so.
''')

WORKFLOWS["hr-portal"] = ("Build the React portal from the Stitch design: Jarvis chat with confirm card, catalog, approvals, audit, dashboard", r'''
Load `stitch-design-pipeline` and `hr-portal-frontend`. Requires `.stitch/DESIGN.md`; if it is missing run `/hr-design` first.

1. Write the typed API client from the contract.
2. Convert the Stitch screens with the `react:components` skill, mapping DESIGN.md tokens to Tailwind and CSS variables. Use real API data, not mocks.
3. Build the five pages with a persona switcher and a Synthetic-data banner. The catalog mirrors the slide's 5 layers and 8 groups.
4. Apply the accessibility fixes from the skill. Make it work at 390px first, then desktop.
// turbo
5. Run `npm run build` and the typecheck. Start backend and frontend together and verify route -> confirm -> result -> switch persona -> approve -> audit.
6. Screenshot each page, list UI issues and fix them.
''')

WORKFLOWS["hr-gemini"] = ("Add the Gemini proposer layer to Jarvis with guardrails, grounding, versioning and evals", r'''
Load `gemini-guardrails` and `jarvis-router`. The deterministic router must already pass its tests.

1. Add `google-genai` and config for `GEMINI_API_KEY`, `GEMINI_MODEL`, `USE_LLM`. Check current model names in the docs.
2. Create `jarvis/prompts/jarvis.v1.md` and record `PROMPT_VERSION`, model and agent version in every audit row.
3. Implement proposal-only routing: structured output -> Pydantic -> allowlist and RBAC validation -> merge with the deterministic score. Show disagreements in the confirm card.
4. Implement input guardrails (length, injection patterns, PII redaction) and output guardrails (schema, refusal path).
5. Implement optional grounded narration with the number-grounding validator.
6. Add timeout, retry, circuit breaker and automatic fallback to the deterministic router. Add `OFFLINE_DEMO`.
7. Extend `evals/golden.seed.jsonl` to >= 100 cases and write `make eval`. Save results to `evals/results/`.
// turbo
8. Run the evals and tests. Fix until accuracy, groundedness and injection resistance meet the gates.
9. Only if time allows and all gates are green, try the optional ADK path from the skill.
''')

WORKFLOWS["hr-quality-gate"] = ("Run the judged-axis gates and print a scorecard with real evidence", r'''
Load `hack-quality-gates` and read `spec/SCORECARD.md`.

// turbo
1. Install dev tooling if missing (ruff, mypy, bandit, pip-audit, pytest-cov, eslint, vitest, playwright, axe).
2. Run every gate for the six axes and capture real output into `docs/evidence/`.
3. Fix failures in the order given in the skill. Maximum two fix rounds.
4. Print the scorecard table with axis, status, evidence, estimated score band, top deduction and fix.
5. List anything not verified. Do not claim a pass without running the check.
''')

WORKFLOWS["hr-govern-scale"] = ("Scale, govern and optimise pass: the differentiator after the build", r'''
Load `gemini-guardrails` and `hack-quality-gates`.

1. **Govern:** agent and prompt version fields in the registry and audit rows, `CHANGELOG.md`, eval history in `evals/results/`, a model risk register in `docs/RISK_REGISTER.md` (hallucination, bias in screening and pay equity, privacy, prompt injection, over-reliance) with the control for each.
2. **Scale:** rate limiting, response caching for read-only agents, DB indexes and query-count tests, pagination, structured JSON logs with a trace id stored in the audit row, Cloud Run settings (concurrency, min instances 1 on demo day, memory) and a short load test with p50 and p95.
3. **Optimise:** bundle size budget, lazy-load pages, Gemini cache and cost counter on the dashboard.
4. Write `docs/SCALE_GOVERN_OPTIMISE.md` with before and after numbers.
// turbo
5. Re-run `/hr-test` and report any regression.
''')

WORKFLOWS["hr-align"] = ("Map the official problem statement and judging criteria to features, tests and priorities", r'''
1. Ask the user to paste the official problem statement and judging criteria (or the link and key points). If none yet, use `spec/PRD.md` and `spec/SCORECARD.md`.
2. Write `docs/TRACEABILITY.md`: requirement -> agent or feature -> test -> demo step. Flag requirements with no feature and features with no requirement.
3. Update priorities in `spec/plan.json` (must, should, could) so the critical path serves the stated requirements. Show the diff.
4. Run `python tools/pert.py --hours <hours available>` and report the critical path and the probability of finishing.
''')

WORKFLOWS["hr-replan"] = ("Replan with PERT/CPM when time, scope or conditions change", r'''
Load `hack-pert-planner`.

1. Ask: total hours, hours used, tasks done, and what changed (blocked integration, no Stitch, no Gemini key, new requirement).
2. Update `spec/plan.json` for the change.
// turbo
3. Run `python tools/pert.py --hours <H> --elapsed <E> --done <ids>` (add `--serial` for one builder).
4. Show the critical path, probability of finishing and suggested cuts. Apply cuts only with the user's OK, never cutting tests, security or accessibility.
5. Update `docs/PLAN_STATUS.md` and continue with the next critical task.
''')

WORKFLOWS["hr-sprint"] = ("Time-boxed hackathon mode: plan with PERT/CPM, run the critical path first, replan as you go", r'''
Load `hack-pert-planner` and `hack-quality-gates`. Work in planning mode.

1. Ask for total hours available and anything already done. Run `/hr-align` if the problem statement is known.
// turbo
2. Run `python tools/pert.py --hours <H>`. Show the critical path, the probability of finishing and suggested cuts. Ask once to apply cuts.
3. Execute tasks in plan order using each task's `cmd` workflow. Run independent tasks in parallel agents where dependencies allow; critical tasks first.
4. After each task, run its tests, record progress in `docs/PLAN_STATUS.md` and re-run `python tools/pert.py` with `--elapsed` and `--done`. Announce any change to the critical path.
5. When 15% of the time remains: stop adding features, run `/hr-quality-gate`, then `/hr-deploy` (ask first), `/hr-pitch` and `/hr-submit`.
''')

WORKFLOWS["hr-pitch"] = ("Create the pitch, README, architecture diagram, demo-safe cache and social posts", r'''
Load `hack-pitch-submission`.

1. Write `README.md` and `docs/ARCHITECTURE.md` (Mermaid) with the scorecard evidence from `docs/evidence/`.
2. Run `/hr-demo-script` for the walkthrough, then record golden responses for the demo prompts into `backend/app/demo_cache.json` and test with `OFFLINE_DEMO=true`.
3. Write the 3-minute pitch in `docs/PITCH.md` using the structure in the skill, mapped to the judged axes.
4. Write three social post drafts in `docs/SOCIAL.md`.
5. Produce a screenshot checklist and list what is still missing.
''')

WORKFLOWS["hr-submit"] = ("Final submission checklist with verification", r'''
1. Run `/hr-quality-gate` and `/hr-test`; paste the results table into the README.
2. Verify the public URL on a mobile viewport, the demo passcode, the synthetic-data banner, and that no secrets are in the repo (`git grep` for keys) or history.
3. Confirm `docs/TRACEABILITY.md`, `docs/PITCH.md`, `docs/DEMO_SCRIPT.md`, `docs/evidence/` and the backup screen recording exist.
4. Print a go or no-go list with any blocker at the top.
''')

WORKFLOWS["hr-build-all"] = ("Build the full HR agent demo end to end, stage by stage, with checkpoints", r'''
Use the `hr-stack-architecture` skill. Work in planning mode and keep a task list. After each stage run its tests, summarise results, and continue only if green. `/hr-design` can run in a parallel agent while the backend is built.

1. Run `/hr-status`. If a problem statement exists, run `/hr-align`.
2. Run `/hr-scaffold`.
3. Run `/hr-stitch-setup` (skip with a note if the user has no Stitch access).
4. Run `/hr-database`.
5. Run `/hr-framework`.
6. Run `/hr-agents-employee` and `/hr-agents-infra`.
7. Run `/hr-jarvis`, then `/hr-gemini`.
8. Run `/hr-api`.
9. Run `/hr-design`, then `/hr-portal`.
10. Run `/hr-test`, then `/hr-quality-gate`, then `/hr-govern-scale`.
11. Run `/hr-pitch`.
12. Ask the user whether to run `/hr-deploy`, then `/hr-submit`. Do not deploy without confirmation.
For a time-boxed event use `/hr-sprint` instead.
''')

PRD += r'''
## Hackathon framing
Judged on Code Quality, Security, Efficiency, Testing, Accessibility and Problem Statement Alignment (`SCORECARD.md`). Differentiators: guardrails and grounding, versioning, evals, and a scale/govern/optimise pass. Architecture rule: **the model proposes, pure code decides**. UI designed in Google Stitch (`DESIGN_BRIEF.md`). Planning is quantitative (`plan.json`, `tools/pert.py`).
'''

README = r'''# HR Agent Stack: Antigravity build kit (v2, hackathon edition)

Generated by `setup_hr_agents_antigravity.py`.

## Quick start
1. Open this folder in **Google Antigravity**.
2. Read `STITCH_SETUP.md` (5 min) to connect the Stitch MCP and install the Stitch skills. Optional: everything falls back without it.
3. In the agent panel (planning mode) type one of:
   - `/hr-sprint`: time-boxed hackathon mode (PERT/CPM plan, critical path first, replans as you go)
   - `/hr-build-all`: full guided build with checkpoints
   - or stage by stage: `/hr-scaffold` `/hr-stitch-setup` `/hr-database` `/hr-framework` `/hr-agents-employee` `/hr-agents-infra` `/hr-jarvis` `/hr-gemini` `/hr-api` `/hr-design` `/hr-portal` `/hr-test` `/hr-quality-gate` `/hr-govern-scale` `/hr-pitch` `/hr-deploy` `/hr-submit`
4. Helpers: `/hr-status` `/hr-align` (paste the official problem statement) `/hr-replan` `/hr-add-agent` `/hr-demo-script`

## What is here
- `.agent/rules/`: always-on rules (model proposes, code decides; judged axes; time box)
- `.agent/skills/`: 13 skills. Domain-agnostic: `stitch-design-pipeline`, `gemini-guardrails`, `hack-quality-gates`, `hack-pert-planner`, `hack-pitch-submission`. HR-specific: the `hr-*` skills.
- `.agent/workflows/`: the slash commands
- `spec/`: `agents.json` (40 agents), `personas.json`, `layers.json`, `PRD.md`, `DESIGN_BRIEF.md`, `SCORECARD.md`, `plan.json`
- `tools/pert.py`: PERT/CPM planner. `tools/mcp/`: Stitch MCP config examples
- `evals/golden.seed.jsonl`: 40 seed routing cases

## Notes
If slash commands do not appear, your Antigravity version may use `.agents/`; re-run the generator with `--both`.
Stitch/MCP config formats and model names change; verify against current docs.
'''

PERSONA_FOR_GROUP = {"Talent": "recruiter", "Onboarding": "recruiter", "Talent Mgmt & Dev": "hrbp",
                     "Business Partners": "hrbp", "People Operations": "hr_head", "Total Rewards": "comp_lead",
                     "People Analytics": "hrbp", "HR Technology": "governance"}


def golden_seed(reg):
    emp = set(next(p for p in PERSONAS if p["id"] == "employee")["allow_agents"])
    rows = []
    for a in reg:
        persona = "employee" if a["id"] in emp else PERSONA_FOR_GROUP[a["group"]]
        rows.append(json.dumps({"ask": a["ask"], "expected_agent": a["id"], "persona": persona}, ensure_ascii=False))
    return "\n".join(rows) + "\n"


def self_check(root, reg):
    """Validate the generated pack; returns a list of problems (empty = OK)."""
    problems = []
    if len({a["id"] for a in reg}) != 40:
        problems.append("agent ids are not 40 unique values")
    plan_ids = {t["id"] for t in PLAN}
    for t in PLAN:
        for d in t["deps"]:
            if d not in plan_ids:
                problems.append(f"plan task {t['id']} depends on unknown {d}")
        if t["cmd"].lstrip("/") not in WORKFLOWS:
            problems.append(f"plan task {t['id']} points to missing workflow {t['cmd']}")
    for name, (_, body) in WORKFLOWS.items():
        for ref in re.findall(r"`/(hr-[a-z-]+)`", body):
            if ref not in WORKFLOWS:
                problems.append(f"workflow {name} references missing /{ref}")
    for name, (desc, body) in SKILLS.items():
        if not desc.strip() or not body.strip():
            problems.append(f"skill {name} is empty")
    for rel in ("spec/agents.json", "spec/personas.json", "spec/layers.json", "spec/plan.json"):
        try:
            json.loads((root / rel).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{rel} invalid: {exc}")
    return problems


# ----------------------------------------------------------------------------
# 6. WRITER
# ----------------------------------------------------------------------------
def agents_table(reg):
    lines = ["# The 40 agents", "", "| # | Layer | Group | Agent | Sample ask | Approval |", "|---|---|---|---|---|---|"]
    for i, a in enumerate(reg, 1):
        lines.append(f"| {i} | {a['layer']} | {a['group']} | {a['name']} | {a['ask']} | {a['approval']} |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Generate Antigravity skills + slash commands for the HR 40-agent demo")
    ap.add_argument("--target", default="hr-agent-stack", help="project folder to create (default: ./hr-agent-stack)")
    ap.add_argument("--agent-dir", default=".agent", help="Antigravity config folder name (default: .agent)")
    ap.add_argument("--both", action="store_true", help="also write the .agents/ variant")
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    args = ap.parse_args()

    root = Path(args.target).expanduser().resolve()
    reg = build_registry()
    written, skipped = [], []

    def w(rel, text):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and not args.force:
            skipped.append(rel)
            return
        p.write_text(text.lstrip("\n"), encoding="utf-8")
        written.append(rel)

    # spec
    w("spec/agents.json", json.dumps(reg, indent=2, ensure_ascii=False) + "\n")
    w("spec/personas.json", json.dumps(PERSONAS, indent=2, ensure_ascii=False) + "\n")
    w("spec/layers.json", json.dumps(LAYERS, indent=2, ensure_ascii=False) + "\n")
    w("spec/agents.md", agents_table(reg))
    w("spec/PRD.md", PRD)
    w("README.md", README)
    w("spec/DESIGN_BRIEF.md", DESIGN_BRIEF)
    w("spec/SCORECARD.md", SCORECARD)
    w("spec/plan.json", json.dumps({"reserve_pct": 0.15, "tasks": PLAN}, indent=2) + "\n")
    w("tools/pert.py", PERT_PY)
    w("tools/mcp/stitch.official.example.json", MCP_OFFICIAL)
    w("tools/mcp/stitch.proxy.example.json", MCP_PROXY)
    w("STITCH_SETUP.md", STITCH_SETUP)
    w("evals/golden.seed.jsonl", golden_seed(reg))
    w("docs/DECISIONS.md", "# Decisions\n\n(Log choices and trade-offs here: Stitch available or not, model used, cuts made.)\n")
    w("docs/PLAN_STATUS.md", "# Plan status\n\nDone:\nIn progress:\nNext:\nCuts:\nRisks:\n")
    w(".gitignore", ".env\n__pycache__/\n*.pyc\n.venv/\nnode_modules/\ndist/\n.DS_Store\n")

    dirs = [args.agent_dir] + ([".agents"] if args.both and args.agent_dir != ".agents" else [])
    for d in dirs:
        w(f"{d}/rules/hr-agents.md", RULE)
        for name, (desc, body) in SKILLS.items():
            w(f"{d}/skills/{name}/SKILL.md", f"---\nname: {name}\ndescription: {desc}\n---\n{body}")
        for name, (desc, body) in WORKFLOWS.items():
            w(f"{d}/workflows/{name}.md", f"---\ndescription: {desc}\n---\n{body}")

    problems = self_check(root, reg)
    print("\nSelf-check:", "OK" if not problems else "PROBLEMS")
    for p in problems:
        print("  -", p)
    print(f"\nProject: {root}")
    print(f"Agents in registry: {len(reg)}  |  skills: {len(SKILLS)}  |  slash commands: {len(WORKFLOWS)}")
    print(f"Written: {len(written)} files" + (f"  (skipped existing: {len(skipped)}, use --force)" if skipped else ""))
    print("\nNext steps:")
    print(f"  1. Open {root} in Google Antigravity")
    print("  2. Read STITCH_SETUP.md, then in the agent panel type:  /hr-sprint   (time-boxed)  or  /hr-build-all")
    print("  3. Slash commands: " + " ".join("/" + n for n in WORKFLOWS))
    if not args.both:
        print("\nTip: if slash commands do not appear, re-run with --both (writes .agents/ too).")


if __name__ == "__main__":
    main()
