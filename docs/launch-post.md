# Launch post — LinkedIn / Hacker News / LocalGov Digital

## LinkedIn (Alfred, public)

UK councils deserve the same AI tools as central government.

Open source. Auditable. Cyber Essentials ready. And designed from line one to pass an EU AI Act audit — not retrofitted after a regulator comes knocking.

That's why I've been building **civiclaw** — a sovereign, on-prem agent runtime for UK public sector. First skill shipped: a DSAR agent that takes a real Subject Access Request and walks it through intake → search → redact → respond in minutes, not the 20+ hours a council typically spends.

Every stage writes to a cryptographic append-only audit log that regulators can verify. Every action that drafts a response pauses for a human sign-off, because Article 14 of the AI Act says it has to. Every skill lives or dies by the regulatory mapping it declares — no hand-wavy "AI compliance" claims.

The thesis is simple: US-hosted, closed-source AI vendors will not win UK public sector. Sovereign, auditable, open-source runtimes will. The EU AI Act Annex III deadline (2 August 2026) and G-Cloud 15 award (17 September 2026) turn it from a nice-to-have into a procurement requirement.

Apache 2.0. Free to run on your own infrastructure. Paid hosted tier for councils who want Cyber Essentials Plus, SLA and support.

Repo → [github.com/workloft/civiclaw] (link live soon)

If you work in Local Authority IT, Information Governance, or procurement — I want your feedback. DM me. The next skills I build are the ones you tell me you need first.

---

## Hacker News (Show HN)

**Show HN: civiclaw — open-source audit-native agent runtime for UK public sector**

I've been building an agent runtime specifically for UK Local Authorities and NHS Trusts. First skill is a UK GDPR Subject Access Request handler that walks the full lifecycle (intake → source discovery → third-party redaction → compliant response draft) and logs every step to a cryptographic append-only audit log that verifies tamper-evident.

Design constraints:
- Every skill declares its regulatory mappings in YAML frontmatter (UK GDPR article, EU AI Act article, ICO code of practice). Skills that don't declare mappings don't load.
- The audit log is a primitive, not an option. Append-only, hash-chained, no delete path. Designed to produce EU AI Act Article 12 evidence.
- Human-in-the-loop is structural. Any stage marked `human_in_the_loop` blocks on an approval audit event.
- Model-agnostic. Claude is the dev default; Ollama/Qwen is the sovereign fallback so a council can run it with zero US-lab dependency.

The motivation: US SaaS incumbents (OneTrust, Vanta, DataGrail) don't chase £10k-£30k council budgets. UK public sector has been duct-taping Excel + Outlook + Word macros to meet legal obligations. EU AI Act Annex III kicks in August 2026. There's a gap big enough to walk through.

Apache 2.0. Single-developer built, AI-augmented (I document that honestly in CONTRIBUTING).

Repo → [link]
Architecture → [link to docs/architecture.md]
Compliance mapping → [link to docs/compliance-mapping.md]

Feedback especially welcome from: public-sector IT, information-governance practitioners, and anyone who has actually shipped an EU AI Act conformity assessment.

---

## LocalGov Digital Slack (post to #ai)

Hi all — quick share. I've been working on an open-source agent runtime specifically for UK councils, called civiclaw.

The first skill takes a UK GDPR Subject Access Request and walks it through intake → system search → third-party redaction → compliant response draft. Every action logs to a tamper-evident audit trail that satisfies EU AI Act Article 12 (the 6-month logging requirement). Every draft response pauses for human sign-off before anything leaves the agent.

It's free, Apache 2.0, and designed to run on council infrastructure (not a US-hosted SaaS). Claude Sonnet is the dev default; local Ollama/Qwen is the sovereign fallback for anyone who can't/won't send council data to a US lab.

I'm looking for 2–3 councils willing to pilot it against a real DSAR backlog. Happy to do the setup, the training, and the first pass with you. If you're interested — DM me here or email alfred@workloft.ai.

Repo and docs: [link]

---

## Notes

- Publish LinkedIn version after the GitHub repo is public.
- HN version saved for the Sunday evening US-Monday-morning HN window.
- LocalGov Digital version is the highest-conversion channel per research; post within 48 hours of the GitHub repo going live.
