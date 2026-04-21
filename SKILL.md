# civiclaw SKILL.md format

Every civiclaw skill lives in `skills/<name>/` and ships a `SKILL.md` that tells the runtime how to load it, what it claims to do, and which regulatory obligations it maps to.

## Minimum viable skill

```
skills/my-skill/
├── SKILL.md           (required — this file)
├── skill.py           (required — entry point)
├── config.py          (optional — mock data, model config)
├── samples/           (optional — fixtures for testing and demos)
└── tests/             (optional — pytest cases)
```

## SKILL.md format

```yaml
---
name: my-skill                       # unique, lowercase-hyphen
version: 0.1.0                       # semver
summary: One-sentence description.
entry: skill.py                      # path relative to this SKILL.md
commands:                            # CLI subcommands the skill exposes
  - name: intake
    description: Parse an incoming request.
    args: ["<path-or-text>"]
  - name: respond
    description: Draft a compliant response.
    args: ["--request-id"]
compliance_mappings:                 # regulatory artefacts this skill supports
  - uk_gdpr_article_15
  - dpa_2018_part_3
  - eu_ai_act_article_12
  - eu_ai_act_article_14
model_tier: mid                      # cheap | mid | frontier
audit_events:                        # events this skill MUST emit to the audit log
  - intake.parsed
  - search.planned
  - redaction.applied
  - response.drafted
human_in_the_loop:                   # stages that block on a human sign-off
  - response.drafted
---

# My Skill

Longer-form description of what this skill does, who uses it, and which
compliance obligations it discharges.

## Usage

Document the CLI, expected inputs/outputs, and any environment variables.

## Compliance evidence

For each `compliance_mappings` entry, describe how this skill's outputs
satisfy the obligation. This is what a regulator will read.

## Failure modes

What can go wrong, and what the skill does when it does.
```

## Rules

1. Every skill MUST emit audit events for every state transition — no silent decisions.
2. Every skill MUST declare `compliance_mappings` honestly. If you can't produce regulator-facing evidence, don't claim the mapping.
3. Every skill MUST support a `--dry-run` mode that exercises the full flow without sending real emails, filing real documents or mutating real data.
4. Every skill MUST use the runtime's model router, not call model APIs directly — this keeps the sovereign-fallback promise intact.
5. Every skill SHOULD include samples/ that let a new contributor demo the skill in under 60 seconds.

## Loading

At runtime, `core/runtime.py` discovers every `skills/*/SKILL.md`, validates the YAML frontmatter, and registers the skill's commands with the CLI + admin UI. No manual registration required.
