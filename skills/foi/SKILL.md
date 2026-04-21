---
name: foi
version: 0.1.0-scaffold
summary: Freedom of Information Act 2000 request handling — qualification, search, response drafting.
entry: skill.py
commands:
  - name: intake
    description: Parse an incoming FOI request, identify applicable exemptions.
    args: ["<path-or-text>"]
compliance_mappings:
  - foia_2000
  - ico_foi_code_of_practice
  - eu_ai_act_article_12
model_tier: mid
audit_events:
  - intake.parsed
  - exemption.applied
  - response.drafted
human_in_the_loop:
  - response.drafted
---

# FOI skill (scaffold)

**Status:** scaffold. Not implemented.

This skill will handle the full Freedom of Information Act 2000 lifecycle for UK Local Authorities:

- Intake: parse the request, qualify against s.1 (the duty to confirm or deny), identify applicable absolute and qualified exemptions (s.21–s.44).
- Fee estimation: s.12 cost-limit assessment (£450 or 18 hours).
- Search: identify departments / systems likely to hold the requested information.
- Response drafting: section-by-section response with exemption rationale, public interest test (for qualified exemptions), and the mandatory rights-to-appeal text.

Coming in v0.2 — track progress at [workloft.ai](https://workloft.ai) or the project issues.
