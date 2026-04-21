---
name: foi
version: 0.1.0
summary: UK FOIA 2000 request handling — qualification, s.12 fee check, search, response drafting.
entry: skill.py
commands:
  - name: intake
    description: Parse a FOI request, qualify against s.1, flag likely exemptions.
    args: ["<path-or-text>"]
  - name: fee-check
    description: s.12 cost-limit assessment (£450 / 18 hours for LAs).
    args: ["<path-or-text>"]
  - name: search
    description: Plan which council departments likely hold the info.
    args: ["<path-or-text>"]
  - name: respond
    description: Draft the FOI response letter with exemption rationale and appeal rights.
    args: ["--request-id"]
compliance_mappings:
  - foia_2000
  - foia_2000_s_12
  - foia_2000_s_14
  - foia_2000_s_40
  - eir_2004
  - ico_foi_code_of_practice
  - dpa_2018_part_2
  - eu_ai_act_article_12
  - eu_ai_act_article_14
model_tier: mid
audit_events:
  - intake.parsed
  - fee_limit.assessed
  - search.planned
  - response.drafted
human_in_the_loop:
  - response.drafted
---

# FOI skill

Handles the full lifecycle of a UK Freedom of Information Act 2000 request for a Local Authority IG team.

| Stage | Command | Output |
|---|---|---|
| Intake | `intake` | Qualification against s.1, likely exemptions flagged, clarification questions, risks and next steps |
| Fee check | `fee-check` | s.12 cost-limit assessment with task-by-task time estimate; verdict within-limit / at-risk / exceeds |
| Search | `search` | Cross-department search plan, prioritised, with rough hours |
| Respond | `respond` | Draft response letter with exemption rationale, public-interest test, appeal rights footer |

## Usage

```bash
civiclaw foi intake skills/foi/samples/sample_request.txt
civiclaw foi fee-check skills/foi/samples/sample_request.txt
civiclaw foi search skills/foi/samples/sample_request.txt
civiclaw foi respond --request-id FOI-2026-001
civiclaw approve --ref FOI-2026-001 --note "Response cleared by IGO."
```

## Compliance evidence

- **FOIA 2000 s.1 (duty to confirm or deny).** `intake` explicitly qualifies the request against s.1 and flags anything that prevents the 20-working-day clock from starting.
- **FOIA 2000 s.12 (cost limit).** `fee-check` produces a task-by-task time estimate against the £450 / 18-hour threshold; the assessment is logged to the audit trail as `fee_limit.assessed` with the limits and computed total.
- **FOIA 2000 s.14 (vexatious requests).** `intake` includes repeat / vexatious detection in its checklist.
- **FOIA 2000 s.40 (personal data).** `respond` carves out third-party personal data with UK GDPR lawful-basis citation.
- **EIR 2004 (environmental information).** `intake` detects environmental scope and routes the request under s.39 FOIA to the EIR regime.
- **ICO FOI Code of Practice (2018).** Prompts are aligned to the mandatory response components: s.1 confirmation, exemption citation, PIT reasoning, internal-review rights, ICO appeal rights.
- **EU AI Act Art. 12.** Every stage emits a structured audit event (intake.parsed, fee_limit.assessed, search.planned, response.drafted) with ≥6-month retention via the core audit log.
- **EU AI Act Art. 14.** `response.drafted` is marked `human_in_the_loop`; the runtime requires a `civiclaw approve --ref <id>` sign-off before the draft leaves the agent.

## Failure modes

- **Environmental information mis-routed.** Intake detects and flags; but if the IGO overrides, the audit log captures the override as a separate event.
- **s.36 qualified-person opinion not yet sought.** If the drafted response relies on s.36, the skill flags "requires qualified-person opinion" and refuses to mark the response ready-to-send until a corresponding audit entry is logged.
- **Aggregation of related requests (Reg 5).** Currently detected at intake only; multi-request aggregation across the council's inbox is a v0.2 feature.

## Production roadmap

- Automatic qualified-person workflow for s.36 invocations
- EIR 2004 sibling skill for pure environmental information requests
- FOI inbox integration (email, WhatDoTheyKnow.com) with automatic deduplication
- Batch processing for response generation across a month's backlog
- Dashboard widget for 20-day deadline tracking with ICO-aligned extension logic
