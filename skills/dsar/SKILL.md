---
name: dsar
version: 0.1.0
summary: UK GDPR Article 15 Subject Access Request intake, search, redaction and response.
entry: skill.py
commands:
  - name: intake
    description: Parse an incoming DSAR request.
    args: ["<path-or-text>"]
  - name: search
    description: Identify LA data sources likely to hold the subject's data.
    args: ["<subject-name>"]
  - name: redact
    description: Redact third-party personal data from a document.
    args: ["<document>", "--subject"]
  - name: respond
    description: Draft a UK GDPR-compliant response letter.
    args: ["--request-id"]
compliance_mappings:
  - uk_gdpr_article_15
  - uk_gdpr_article_15_4
  - dpa_2018_part_3
  - ico_sar_code_of_practice
  - eu_ai_act_article_12
  - eu_ai_act_article_14
model_tier: mid
audit_events:
  - intake.parsed
  - search.planned
  - redaction.applied
  - response.drafted
human_in_the_loop:
  - response.drafted
---

# DSAR skill

Handles the four stages of a UK GDPR Subject Access Request for a Local Authority information-governance team.

| Stage | Command | Output |
|---|---|---|
| Intake | `intake` | Parsed request object (requester, subject, scope, verification status, urgency flags, next steps) |
| Search | `search` | Prioritised list of LA data sources to query, with rationale |
| Redact | `redact` | Document with third-party personal data redacted, preserving subject's own data |
| Respond | `respond` | Draft response letter citing UK GDPR Articles 12–15 and DPA 2018 provisions |

## Usage

```bash
python3 skill.py intake sample_request.txt
python3 skill.py search "James Wilson"
python3 skill.py redact sample_document.txt --subject "James Wilson" --requester "Sarah Wilson"
python3 skill.py respond --request-id REQ001
```

## Compliance evidence

- **UK GDPR Art. 15** — this skill exists to answer the right of access; every response includes the required categories of personal data, recipients, retention, source origin, and rights-to-rectification/erasure text.
- **UK GDPR Art. 15(4)** — third-party data redaction preserves the rights and freedoms of others; redaction log is emitted to the civiclaw audit trail.
- **DPA 2018 Part 3/4** — supplementary UK-specific provisions cited in the generated response letters.
- **ICO SAR Code of Practice** — the intake and search prompts are aligned to the ICO's 2023 update; the response draft includes the mandatory information categories.
- **EU AI Act Art. 12** — every stage emits a structured audit event (intake.parsed, search.planned, redaction.applied, response.drafted) for ≥6-month retention.
- **EU AI Act Art. 14** — `response.drafted` is marked `human_in_the_loop`; the runtime must require a human sign-off before any draft leaves the agent.

## Failure modes

- **Requester identity unverified.** The intake stage flags it and does NOT auto-advance to search. Human must confirm ID before progressing.
- **Ambiguous scope.** The intake returns `risks_and_blockers` with specific clarification questions.
- **Document too large for model context.** Redact stage chunks the document, processes per chunk, logs the chunk boundaries in the audit trail.
- **Model refuses / returns non-JSON.** Skill falls back to a structured extraction prompt and logs `model.fallback` in the audit trail.

## Production roadmap

- Integration with LA document management systems (M-Files, iManage, SharePoint)
- Identity-verification workflow (GOV.UK Verify, council customer portals)
- Batch processing across multiple documents
- Exemption management (Schedule 2 DPA 2018 exemptions, LPP, crime prevention)
- Automated deadline tracking with ICO-compliant extension logic
