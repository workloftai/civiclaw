"""
civiclaw runtime — discovers and loads skills from ./skills/*/SKILL.md.

A skill is valid if:
  * its directory contains a SKILL.md
  * the SKILL.md starts with a YAML frontmatter block between `---` markers
  * the frontmatter includes: name, version, entry, compliance_mappings

Skills are registered but NOT executed by the runtime — the caller invokes
them via the CLI entry point declared in SKILL.md. The runtime's job is
discovery, validation, and audit-logging the fact that a skill was invoked.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SKILL_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


@dataclass
class Skill:
    name: str
    version: str
    summary: str
    entry: str
    path: Path
    commands: list[dict[str, Any]]
    compliance_mappings: list[str]
    audit_events: list[str]
    human_in_the_loop: list[str]
    model_tier: str


def _parse_yaml_lite(text: str) -> dict[str, Any]:
    """Minimal YAML-ish parser — sufficient for SKILL.md frontmatter without a PyYAML dependency.

    Supports scalars, simple lists, and nested lists of dicts at one level. This
    is intentionally tiny; anything more elaborate belongs in PyYAML which we
    add when the runtime matures past the prototype.
    """
    result: dict[str, Any] = {}
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" not in line:
            i += 1
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "":
            # Nested list of scalars or dicts follows.
            values: list[Any] = []
            j = i + 1
            while j < len(lines) and lines[j].startswith(" "):
                item = lines[j].strip()
                if item.startswith("- "):
                    val = item[2:].strip()
                    if ":" in val and not val.startswith('"'):
                        # List of dicts: start a new dict entry, parse nested.
                        d: dict[str, Any] = {}
                        k, _, v = val.partition(":")
                        d[k.strip()] = _coerce(v.strip())
                        jj = j + 1
                        while jj < len(lines) and lines[jj].startswith("    "):
                            inner = lines[jj].strip()
                            if ":" in inner:
                                ik, _, iv = inner.partition(":")
                                d[ik.strip()] = _coerce(iv.strip())
                            jj += 1
                        values.append(d)
                        j = jj
                        continue
                    values.append(_coerce(val))
                j += 1
            result[key] = values
            i = j
        else:
            result[key] = _coerce(rest)
            i += 1
    return result


def _coerce(value: str) -> Any:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value.startswith("["):
        # inline list: ["a", "b", "c"]
        inner = value.strip("[]")
        if not inner.strip():
            return []
        return [_coerce(v.strip()) for v in inner.split(",")]
    return value


def load_skill(skill_dir: Path) -> Skill | None:
    manifest = skill_dir / "SKILL.md"
    if not manifest.exists():
        return None
    text = manifest.read_text(encoding="utf-8")
    match = SKILL_FRONTMATTER_RE.search(text)
    if not match:
        return None
    meta = _parse_yaml_lite(match.group(1))
    required = ["name", "version", "entry", "compliance_mappings"]
    if any(k not in meta for k in required):
        return None
    return Skill(
        name=meta["name"],
        version=meta["version"],
        summary=meta.get("summary", ""),
        entry=meta["entry"],
        path=skill_dir,
        commands=meta.get("commands", []) or [],
        compliance_mappings=meta.get("compliance_mappings", []) or [],
        audit_events=meta.get("audit_events", []) or [],
        human_in_the_loop=meta.get("human_in_the_loop", []) or [],
        model_tier=meta.get("model_tier", "mid"),
    )


def discover_skills(root: Path | str = "skills") -> list[Skill]:
    """Walk root/*/SKILL.md and return the list of valid skills."""
    root = Path(root)
    if not root.exists():
        return []
    skills: list[Skill] = []
    for sub in sorted(root.iterdir()):
        if not sub.is_dir():
            continue
        skill = load_skill(sub)
        if skill:
            skills.append(skill)
    return skills


if __name__ == "__main__":
    # Smoke test — print the skills the runtime can see.
    for skill in discover_skills(Path(__file__).parent.parent / "skills"):
        print(f"{skill.name} v{skill.version} — {skill.summary}")
        print(f"  entry: {skill.path / skill.entry}")
        print(f"  compliance: {', '.join(skill.compliance_mappings)}")
        print(f"  audit events: {', '.join(skill.audit_events)}")
        if skill.human_in_the_loop:
            print(f"  human-in-the-loop: {', '.join(skill.human_in_the_loop)}")
