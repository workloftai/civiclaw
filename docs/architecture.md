# civiclaw architecture

## One-line summary

A skill-based agent runtime where every skill is a self-contained module declaring its own regulatory mappings, audit events, and human-oversight gates — discovered at load time, executed under a single cryptographic audit log, and routed through a model-agnostic brain so the same skill can run on Claude, GPT, Gemini, or a local sovereign Ollama/Qwen model.

## Diagram (text)

```
                  ┌─────────────────────────────────┐
                  │            Admin UI             │  Next.js, local
                  │  (review, approve, inspect log) │
                  └───────────────┬─────────────────┘
                                  │
                                  ▼
                  ┌─────────────────────────────────┐
                  │        core/runtime.py          │
                  │  - discover skills/*/SKILL.md   │
                  │  - validate frontmatter         │
                  │  - register commands            │
                  └───────────────┬─────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
  ┌──────────┐             ┌──────────┐             ┌──────────┐
  │ skills/  │             │ skills/  │             │ skills/  │
  │  dsar/   │             │  foi/    │             │  <next>/ │
  └────┬─────┘             └────┬─────┘             └────┬─────┘
       │                        │                        │
       └────────────────────────┼────────────────────────┘
                                │
                                ▼
                  ┌─────────────────────────────────┐
                  │       core/audit.py             │
                  │  append-only, hash-chained      │
                  │  JSONL file (EU AI Act Art. 12) │
                  └─────────────────────────────────┘
                                │
                                ▼
                  ┌─────────────────────────────────┐
                  │       model router (tbd)        │
                  │  Claude / GPT / Gemini / Qwen   │
                  │  Ollama fallback for sovereign  │
                  └─────────────────────────────────┘
```

## Design principles

### 1. Skills are manifest-first

A skill is defined by its `SKILL.md` frontmatter, not by its code. The runtime refuses to load a skill whose manifest doesn't declare `compliance_mappings`. This keeps regulatory claims honest: a skill cannot silently claim to handle DPA 2018 compliance.

### 2. The audit log is a primitive

Everything that happens goes through `core/audit.py`. Not "can be configured to go through" — goes through. Skills import `AuditLog` and write events as part of their normal flow. The log is append-only and hash-chained, so any edit or deletion is detectable by `AuditLog.verify()`.

Design constraint: there is no delete path. This is intentional. A regulator who asks for evidence must get complete evidence, not evidence the operator chose to preserve.

### 3. Human-in-the-loop is structural

Article 14 of the EU AI Act mandates effective human oversight on high-risk systems. civiclaw enforces this by requiring skills to declare which stages are `human_in_the_loop` in their SKILL.md. The runtime blocks those stages until a sign-off is logged. The admin UI is where sign-offs happen.

### 4. Model-agnostic by design

Today's prototype uses Claude Sonnet 4.6 via the Anthropic SDK because that's what Bob (Alfred's coding agent) already uses and the tooling is mature. But the architecture treats Claude as one implementation of a `model_router` interface. Future work: add OpenAI, Gemini, and Ollama/Qwen backends; the sovereign-fallback Qwen 3.6 lets a council run civiclaw without *any* US-lab cloud dependency.

### 5. No telemetry. No phone-home.

A sovereign runtime can't quietly dial home. Zero analytics, zero crash-reporting to external services, zero dependency on third-party DNS or CDN for core runtime paths. Logs stay on the operator's infrastructure.

### 6. Cyber Essentials posture out of the box

Hardened defaults: no root exec, no open ports other than the admin UI, secrets loaded from a path explicitly configured by the operator (never from a URL), all external calls signed and logged.

## What is NOT in scope (yet)

- Multi-tenancy. The v0.1 runtime is single-org. Multi-tenant SaaS is a hosted-tier concern, not a runtime concern.
- Live document-management integrations. Skills see files on disk; the plumbing to pull from SharePoint / iManage / M-Files is a per-council job, priced separately.
- Built-in identity provider. Skills accept an `actor` ID; the operator's existing SSO (Azure AD, Google Workspace) passes it in.
- Billing. Irrelevant at the runtime layer. The hosted tier handles billing separately.

## What the runtime gives you that the DIY stack doesn't

- A manifest format that forces regulatory honesty on every skill
- A tamper-evident audit log that exists by default, not as an opt-in
- Human-oversight gates as a structural primitive, not an afterthought
- A skill ecosystem that grows without runtime changes — add a skill directory, the runtime picks it up

## Next milestones

- Model router abstraction (next sprint)
- Ollama/Qwen sovereign backend validated end-to-end
- Sigstore-compatible signing of the audit log
- Minimal Next.js admin UI for sign-offs and log inspection
- First paid LA pilot
