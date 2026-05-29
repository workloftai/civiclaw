---
name: aiact
version: 0.1.0
summary: EU AI Act (Regulation 2024/1689) risk classification, Annex IV technical documentation, and Fundamental Rights Impact Assessment for UK public-sector AI systems.
entry: skill.py
commands:
  - name: intake
    description: Parse a plain-English description of an AI system into a structured AI Act profile.
    args: ["<path-or-text>"]
  - name: classify
    description: Classify the system against EU AI Act risk tiers (prohibited / high-risk / limited / minimal) and Annex III triggers.
    args: ["<path-or-text>"]
  - name: annex-iv
    description: Generate Annex IV technical documentation for a high-risk AI system.
    args: ["--request-id"]
  - name: fria
    description: Generate a Fundamental Rights Impact Assessment (Article 27) for a high-risk system deployed by a public authority.
    args: ["--request-id"]
compliance_mappings:
  - eu_ai_act_article_5         # prohibited practices
  - eu_ai_act_article_6         # classification rules for high-risk
  - eu_ai_act_annex_iii         # high-risk systems list (incl. essential public services, education, employment, law enforcement)
  - eu_ai_act_article_9         # risk management system
  - eu_ai_act_article_10        # data and data governance
  - eu_ai_act_article_11        # technical documentation
  - eu_ai_act_annex_iv          # technical documentation contents (the deliverable)
  - eu_ai_act_article_12        # record-keeping (logging) — civiclaw audit log satisfies this
  - eu_ai_act_article_14        # human oversight
  - eu_ai_act_article_27        # FRIA — public-authority deployer obligation
  - uk_gdpr_article_22          # automated decision-making (overlap)
  - ico_ai_auditing_framework
model_tier: mid
audit_events:
  - intake.parsed
  - risk.classified
  - annex_iv.drafted
  - fria.drafted
---

# AI Act skill — civiclaw

This skill helps a UK public-sector deployer (Local Authority, NHS Trust, Housing Association, central government department) classify an AI system against the EU AI Act and produce the documentation a regulator can ask for at any point.

## Why this matters

The EU AI Act (Regulation 2024/1689) entered into force on **1 August 2024**. The high-risk obligations (Articles 6, 9–15) apply from **2 August 2026**. UK organisations are not exempt — any AI system that affects the rights of EU/EEA residents falls in scope, and the UK government has signalled equivalence in its forthcoming AI Bill.

Every UK Local Authority deploying any AI system that touches:
- Education or vocational training (Annex III §3)
- Employment, HR, or workforce management (Annex III §4)
- Access to essential public services or benefits (Annex III §5)
- Law enforcement or migration (Annex III §6, §7)
- Administration of justice (Annex III §8)

…is operating a **high-risk AI system** under Article 6, and must produce:

1. A **risk management system** (Article 9)
2. **Annex IV technical documentation** (Article 11) — the canonical evidence pack
3. **Article 12 logs** with ≥6-month retention — civiclaw's audit chain produces these by default
4. A **Fundamental Rights Impact Assessment** (Article 27) before deployment

This skill produces (2) and (4), and verifies that (3) is in place, automatically.

## Commands

```bash
# Parse a free-text description of the AI system
civiclaw aiact intake skills/aiact/samples/sample_system.txt

# Classify the system against the AI Act risk tiers
civiclaw aiact classify skills/aiact/samples/sample_system.txt

# Generate Annex IV technical documentation
civiclaw aiact annex-iv --request-id AIACT-001

# Generate a Fundamental Rights Impact Assessment
civiclaw aiact fria --request-id AIACT-001
```

## Outputs

`annex-iv` and `fria` produce structured Markdown documents covering every section the EU AI Act requires. The drafts are not sign-off-ready on their own — Article 14 of the AI Act requires human oversight, so every output must be reviewed by a named officer (`civiclaw approve --ref AIACT-001`) before it leaves the agent.

## Limitations (v0.1)

- The classification heuristic is structured-prompt-driven, not a deterministic rules engine. Expect the human reviewer to double-check Annex III mapping against the actual AI Act text.
- The Annex IV draft assumes a single ML model — multi-model / agentic systems need extra sections.
- The FRIA template is the public-authority variant. Private deployers in scope should adapt section 5.

## Dependencies

- Anthropic SDK, `instructor`, `pydantic`. Plain-text stages (`annex-iv`, `fria`) fall back to the sovereign router (Ollama/Qwen) when `ANTHROPIC_API_KEY` is unset — see `core/router.py`. Structured-output stages (`intake`, `classify`) currently still require Anthropic; Ollama tool-use wiring is queued.
