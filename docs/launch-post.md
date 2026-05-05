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

**Title (paste into HN's "Title" field):**

`Show HN: Civiclaw – Open-source audit-native agent runtime for UK public sector`

**URL (paste into HN's "URL" field):**

`https://gitlab.com/Alfpl/civiclaw`

**Text body (post as the first comment on your own submission, immediately after submitting):**

I've been building an agent runtime specifically for UK Local Authorities and NHS Trusts. The thesis: US SaaS incumbents (OneTrust, Vanta, DataGrail) don't chase £10k-£30k council budgets, so UK public sector ends up duct-taping Excel + Outlook + Word to meet binding statutory obligations. The EU AI Act high-risk obligations kick in 2 August 2026. There's a real gap.

What ships in v0.1 (today):

- **DSAR skill** — UK GDPR Article 15. Intake, source discovery, third-party redaction with pre/post hash proof, compliant response draft.
- **FOI skill** — FOIA 2000. Qualification, s.12 £450 / 18-hour cost-limit check, department search plan, response with exemption rationale.
- **EIR skill** — Environmental Information Regulations 2004. Reg 12 / Reg 13 exception analysis with the mandatory public-interest test (and the Reg 12(2) presumption in favour of disclosure), Reg 7 extension awareness.
- **AIact skill** — EU AI Act risk classification, Annex IV technical documentation generator, and Article 27 Fundamental Rights Impact Assessment for public-authority deployers.

Design constraints I've stuck to:

- Every skill declares its regulatory mappings in YAML frontmatter (UK GDPR article, EU AI Act article, ICO code of practice). Skills that don't declare mappings don't load.
- The audit log is a primitive, not an option. Append-only, SHA-256 hash-chained, no delete path. `civiclaw audit verify` walks the chain; tamper one byte and it tells you which row broke. Designed to satisfy EU AI Act Article 12 (the 6-month logging requirement).
- Human-in-the-loop is structural. Any stage marked `human_in_the_loop` blocks on an approval audit event before the output leaves the agent. Article 14 enforced, not optional.
- Model-agnostic. Claude is the dev default; Ollama/Qwen is the sovereign fallback so a council can run it with zero US-lab dependency.
- Skills ship in two paths simultaneously: `skills/<name>/` for the civiclaw runtime, and `.claude/skills/<name>/` for VS Code 1.109+, GitHub Copilot CLI, and Claude Code. Same skill, three IDEs, one audit chain.

Quickstart on a fresh clone takes about 5 minutes — there's a working sample DSAR + FOI + EIR + AI-Act run in the README's quickstart.

Apache 2.0. Single-developer built, AI-augmented (CONTRIBUTING.md is honest about that).

Looking for: feedback from public-sector IT, information-governance practitioners, and anyone who's actually shipped an EU AI Act conformity assessment. What's missing? What would you ship as the next skill?

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
