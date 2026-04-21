# civiclaw

**An open-source, audit-native agent runtime for UK public sector.**

UK councils, NHS Trusts and housing associations deserve the same AI tools as central government — open source, auditable, Cyber Essentials ready, and designed from line one to pass an EU AI Act audit. `civiclaw` is a sovereign, on-prem agent runtime that ships with compliance as the core primitive, not an afterthought.

## The problem

UK public-sector organisations are under binding regulatory pressure:

- **UK GDPR Article 15** — Subject Access Requests must be answered in 30 days. A typical DSAR costs a council 20–40 staff hours.
- **EU AI Act Article 12** — automatic logging with ≥6-month retention, kicking in 2 August 2026 for high-risk systems. Annex IV technical documentation required on demand.
- **Freedom of Information Act** — ~5,000 requests per council per year, each with a 20-working-day clock.
- **Procurement Act 2023 / G-Cloud 15** — social-value reporting, transparency registers, connected-persons declarations.

The market is buying "AI transformation" slide decks. It is not buying auditable, sovereign runtimes that answer to regulators. `civiclaw` is that runtime.

## What it is

A skill-based agent runtime, MIT-friendly (Apache 2.0), designed to:

- Run on-premise or in a UK-sovereign cloud, not a US lab's cloud
- Produce EU AI Act Article 12 logs as a first-class output, not a bolt-on
- Expose every agent action to a cryptographic append-only audit log
- Support any LLM backend — Claude, OpenAI, Gemini, Ollama/Qwen — without vendor lock-in
- Extend via a simple `SKILL.md` format so each compliance domain (DSAR, FOI, AI Act, social-value, transparency register, NHS DSPT, CAFCASS) is a module, not a fork

## Skills shipped today

| Skill | Status | What it does |
|---|---|---|
| [`dsar`](./skills/dsar/) | v0.1 working | Intake, search, redact, and respond to UK GDPR Article 15 requests |
| [`foi`](./skills/foi/) | scaffold | Freedom of Information Act request handling (v0.2) |

## Architecture

```
civiclaw/
├── core/
│   ├── audit.py          cryptographic append-only audit log
│   ├── runtime.py        skill loader, agent router
│   └── policy.py         Art. 14 human-oversight hooks
├── skills/
│   ├── dsar/             first shipped skill
│   │   ├── SKILL.md      skill manifest
│   │   ├── skill.py      agent logic
│   │   └── samples/      demo data
│   └── foi/              second skill (in progress)
├── ui/                   minimal Next.js admin
└── docs/
    ├── architecture.md
    └── compliance-mapping.md   UK GDPR / EU AI Act article mapping
```

## Design principles

1. **Auditable by default.** Every agent decision writes to a Sigstore-compatible append-only log. No action is invisible.
2. **Human-in-the-loop where the law says so.** Article 14 of the EU AI Act requires human oversight on high-risk outputs — `civiclaw` enforces it structurally, not optionally.
3. **Model-agnostic.** Claude is the dev-time default; Ollama/Qwen is the sovereign-fallback primitive. Never locked to one US lab.
4. **Skill-based, not monolithic.** Each compliance obligation is a separate skill. Councils add skills they need; they don't pay for ones they don't.
5. **Cyber Essentials posture from line one.** Hardened defaults. No secrets in code. No telemetry home. No third-party data sharing.

## Quickstart

```bash
git clone <repo>
cd civiclaw
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."

# Run the DSAR skill
python3 skills/dsar/skill.py intake skills/dsar/sample_request.txt
```

See [`skills/dsar/SKILL.md`](./skills/dsar/SKILL.md) for the full DSAR walkthrough.

## Why open source

Because UK councils and NHS Trusts cannot verify what a US-hosted closed-source AI tool does with their data. An open, sovereign, auditable runtime is the only honest answer.

## Roadmap

- **May 2026** — FOI skill, Microsoft 365 + Google Workspace integrations, Next.js admin UI
- **June 2026** — Cryptographic audit log (Sigstore-compatible), human-oversight UI, first Local Authority pilot
- **July 2026** — AI Act conformity pack (Annex IV generator, FRIA wizard)
- **September 2026** — G-Cloud 15 framework listing
- **Q4 2026** — NHS DSPT compliance pack, housing-association skill

## Commercial

The runtime is free and Apache 2.0. For councils that want a hosted Cyber Essentials Plus environment, SLA, and support — see [workloft.ai](https://workloft.ai) for paid tiers.

## Built by

[Workloft.ai](https://workloft.ai) — UK-registered (ICO C1912528), London-based.

## License

Apache License 2.0 — see [LICENSE](./LICENSE).
