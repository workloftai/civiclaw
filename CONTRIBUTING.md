# Contributing to civiclaw

Thanks for considering a contribution. This project is built around one thesis: **UK public-sector agents should be open source, auditable, and answerable to regulators by default.** Everything we accept has to move that thesis forward.

## How to contribute

1. **Report a bug** — open an issue with a reproducible case. If it touches compliance logic or the audit log, mark it `critical`.
2. **Propose a skill** — open an issue titled `skill: <name>`, describe the compliance obligation it discharges, and link to the regulatory reference (UK GDPR article, EU AI Act article, ICO guidance, etc.). We don't build skills without a regulatory anchor.
3. **Ship a skill** — follow [SKILL.md](./SKILL.md). Include `compliance_mappings`, audit events, a `--dry-run` mode, and samples.
4. **Improve the runtime** — especially welcome: audit-log hardening, policy engine work, sovereign-fallback (Ollama/Qwen) reliability.

## What we won't accept

- Skills that don't declare `compliance_mappings`.
- Code that phones home, adds analytics, or adds third-party data sharing.
- Skills that lock to a single LLM vendor.
- Features that bypass the audit log.

## Code style

- Python 3.10+, type hints required on public functions.
- TypeScript strict mode for the admin UI.
- Conventional commits. One logical change per PR.

## Security

Found a vulnerability? Email security@workloft.ai. Please do not open a public issue for security bugs.
