---
name: eir
version: 0.1.0
summary: Environmental Information Regulations 2004 (UK) request handling — intake, exception analysis, search, and response drafting.
entry: skill.py
commands:
  - name: intake
    description: Parse an EIR request, qualify against Reg 5(1), confirm "environmental information" definition under Reg 2(1).
    args: ["<path-or-text>"]
  - name: exception-check
    description: Assess the request against EIR Reg 12 and Reg 13 exceptions; flag the public-interest test.
    args: ["<path-or-text>"]
  - name: search
    description: Plan which council departments and systems likely hold the environmental information.
    args: ["<path-or-text>"]
  - name: respond
    description: Draft the EIR response letter with exception rationale, public-interest reasoning, and rights of appeal.
    args: ["--request-id"]
compliance_mappings:
  - eir_2004                       # the regulations themselves
  - eir_2004_reg_2                 # definition of environmental information
  - eir_2004_reg_5                 # duty to make environmental information available
  - eir_2004_reg_7                 # extension of time for complex requests
  - eir_2004_reg_12                # exceptions (all qualified — public-interest test required)
  - eir_2004_reg_13                # personal data (cousin of FOIA s.40)
  - eir_2004_reg_14                # refusal notice format
  - aarhus_convention              # underlying international instrument
  - directive_2003_4_ec            # underlying EU Directive
  - dpa_2018                       # personal data interactions
  - eu_ai_act_article_12           # civiclaw audit log satisfies record-keeping
  - eu_ai_act_article_14           # human oversight on response drafts
  - ico_eir_code_of_practice
model_tier: mid
audit_events:
  - intake.parsed
  - exceptions.assessed
  - search.planned
  - response.drafted
---

# EIR skill — civiclaw

UK councils handle environmental information requests under the **Environmental Information Regulations 2004** (the EIR), the UK implementation of the Aarhus Convention and the EU Environmental Information Directive (2003/4/EC).

EIR is the regime that catches:
- **Air, water, soil, biodiversity** — pollution monitoring, contamination, ecology
- **Planning + transport** — emissions data, planning applications affecting environmental elements, road schemes
- **Climate** — local authority climate-change plans, carbon footprint reporting
- **Built environment** — when affected by environmental elements (e.g. flooding, air quality)
- **Public health** — to the extent affected by environmental conditions (e.g. air quality near schools)

A typical UK council receives 50–200 EIR requests per year, often from journalists, campaigners, and residents living near roads, planning applications, or industrial sites.

## How EIR differs from FOIA

This is the cousin of the `foi` skill, but with material differences the response draft must respect:

| Dimension | FOIA 2000 | EIR 2004 |
|---|---|---|
| Trigger | Recorded info held by a public authority | Environmental information per Reg 2(1) |
| Timetable | 20 working days | 20 working days; one 20-day extension possible under Reg 7 for complex requests |
| Cost refusal | s.12 — £450 / 18-hour limit | **No equivalent** — charging permitted only for a "reasonable" amount under Reg 8 |
| Exceptions | Mix of absolute and qualified | **All qualified** — every refusal requires a public-interest test |
| Personal data | s.40 | Reg 13 (parallel structure) |
| Form | Must be in writing | Can be oral OR written |
| Appeal | Internal review → ICO | Internal review → ICO (same path) |

## Commands

```bash
civiclaw eir intake samples/sample_request.txt
civiclaw eir exception-check samples/sample_request.txt
civiclaw eir search samples/sample_request.txt
civiclaw eir respond --request-id EIR-2026-001
civiclaw approve --ref EIR-2026-001
civiclaw audit verify
```

## Limitations (v0.1)

- Reg 7 extension drafting is provided as commentary only — the deployer must record the formal Reg 14 notice.
- The personal-data interaction with Reg 13 + UK GDPR is summarised; complex cases (deceased subjects, mixed-purpose data) need DPO review.
- EIR's "environmental information" boundary is sometimes contested. The intake step flags uncertain cases for human review rather than forcing a yes/no.
