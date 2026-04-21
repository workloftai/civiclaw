# Compliance mapping

Every civiclaw skill declares `compliance_mappings` in its SKILL.md frontmatter. This document is the canonical reference for what each mapping means and what evidence the runtime produces.

## UK GDPR

### `uk_gdpr_article_15` — Right of access

**Obligation.** Data subjects may request confirmation of processing and a copy of their personal data within 30 calendar days.

**Evidence civiclaw produces.**
- Audit event `intake.parsed` with requester, subject, scope, date received
- Audit event `search.planned` documenting which systems were queried
- Audit event `response.drafted` with the response text and citation of applicable articles
- Timestamps on every stage suitable for ICO inspection

### `uk_gdpr_article_15_4` — Rights and freedoms of others

**Obligation.** The right of access shall not adversely affect the rights and freedoms of others (basis for third-party redaction).

**Evidence.**
- Audit event `redaction.applied` listing every redaction category applied (names, addresses, phone numbers)
- Cryptographic hash of the pre-redaction and post-redaction documents
- Rationale text explaining why each category was redacted

## UK DPA 2018

### `dpa_2018_part_3` / `dpa_2018_part_4`

**Obligation.** Supplementary UK provisions covering law enforcement processing (Part 3) and intelligence services processing (Part 4), plus the exemptions in Schedules 2–4.

**Evidence.**
- Response drafts cite the correct DPA provisions alongside UK GDPR
- Exemption invocations logged with Schedule and paragraph references

## EU AI Act

### `eu_ai_act_article_12` — Automatic logging

**Obligation.** High-risk AI systems must automatically log events sufficient to ensure traceability, for a minimum retention of 6 months.

**Evidence.** civiclaw's `core/audit.py` is an append-only, hash-chained log. Every skill emits events declared in its SKILL.md `audit_events`. The log is tamper-evident: any edit or deletion breaks the hash chain and `AuditLog.verify()` will return false at the point of tampering.

### `eu_ai_act_article_14` — Human oversight

**Obligation.** High-risk AI systems must be designed to be effectively overseen by humans during the period in which they are in use.

**Evidence.** Every skill declares `human_in_the_loop` stages. The runtime must block those stages on a human sign-off before the skill can progress. The sign-off itself is recorded as an audit event (`oversight.approved` with the approver's identity and timestamp).

## ICO codes of practice

### `ico_sar_code_of_practice`

**Obligation.** Non-binding but authoritative guidance on handling Subject Access Requests. Departing from it requires clear justification.

**Evidence.** The DSAR skill's prompts are aligned to the 2023 update. Generated responses include the mandatory information categories (purposes of processing, categories of data, recipients, retention, source origin, rights to rectification / erasure / restriction / objection, right to complain to ICO).

### `ico_foi_code_of_practice`

**Obligation.** Guidance on handling Freedom of Information requests, including fee notices, exemption application, and public interest tests.

**Evidence.** (Scaffold — FOI skill v0.2.)

## UK FOIA

### `foia_2000`

**Obligation.** Respond to Freedom of Information requests within 20 working days; apply the cost-limit assessment under s.12; apply exemptions under Part II (s.21–s.44) with public interest tests for qualified exemptions.

**Evidence.** (Scaffold — FOI skill v0.2.)

## Why this matters

A regulator inspecting a Local Authority's AI system asks: *"show me the log of how this decision was made."* The civiclaw audit log is that log, structured so the mapping from question to evidence is one query away.

No mapping is claimed that cannot be produced in audit evidence.
