#!/usr/bin/env python3
"""
civiclaw — EU AI Act skill.

Risk-classifies an AI system against EU AI Act (Reg 2024/1689) tiers and Annex III,
generates Annex IV technical documentation (Article 11), and produces a
Fundamental Rights Impact Assessment (Article 27) for public-authority deployers.

Usage:
    skill.py intake     "<system description text or path to .txt>"
    skill.py classify   "<system description text or path to .txt>"
    skill.py annex-iv   --request-id <REQ_ID>
    skill.py fria       --request-id <REQ_ID>

Wiring matches the dsar / foi skills: writes to the civiclaw audit chain at
.audit/civiclaw.jsonl, uses the model router for backend selection, and
respects CIVICLAW_ACTOR for the audit trail.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional

import anthropic
import instructor
from pydantic import BaseModel, Field


# ── Wire to civiclaw runtime ──────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.audit import AuditLog  # noqa: E402

AUDIT_PATH = _REPO_ROOT / ".audit" / "civiclaw.jsonl"
DRAFTS_DIR = _REPO_ROOT / ".audit" / "aiact-drafts"
INTAKE_CACHE = _REPO_ROOT / ".audit" / "aiact-intakes"

_audit = AuditLog(AUDIT_PATH)
ACTOR = os.environ.get("CIVICLAW_ACTOR", "anonymous")
MODEL = os.environ.get("CIVICLAW_AIACT_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = 4096


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _read_text(text_or_path: str) -> str:
    p = Path(text_or_path)
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return text_or_path


def _client() -> anthropic.Anthropic:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    return anthropic.Anthropic(api_key=key)


def _instructor_client():
    return instructor.from_anthropic(_client())


def _call(system: str, user: str) -> str:
    resp = _client().messages.create(
        model=MODEL, max_tokens=MAX_TOKENS, system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text


def _call_structured(system: str, user: str, response_model):
    return _instructor_client().messages.create(
        model=MODEL, max_tokens=MAX_TOKENS, system=system,
        messages=[{"role": "user", "content": user}],
        response_model=response_model,
    )


def _print_section(title: str, body: str) -> None:
    rule = "=" * 72
    print(f"\n{rule}\n  {title}\n{rule}")
    print(body)
    print()


def _save_intake(ref: str, payload: dict) -> Path:
    INTAKE_CACHE.mkdir(parents=True, exist_ok=True)
    path = INTAKE_CACHE / f"{ref}.json"
    path.write_text(json.dumps(payload, indent=2))
    return path


def _load_intake(ref: str) -> dict:
    path = INTAKE_CACHE / f"{ref}.json"
    if not path.exists():
        print(
            f"ERROR: no intake found for ref={ref}. Run `aiact intake` first "
            f"and reuse the printed request id, OR re-run `aiact classify`.",
            file=sys.stderr,
        )
        sys.exit(2)
    return json.loads(path.read_text())


def _save_draft(ref: str, kind: str, body: str) -> Path:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    path = DRAFTS_DIR / f"{ref}-{kind}.md"
    path.write_text(body)
    return path


# ── Pydantic models ───────────────────────────────────────────────────────

class AIActIntake(BaseModel):
    system_name: str = Field(description="Short name of the AI system")
    deployer: str = Field(description="Organisation deploying the system")
    purpose: str = Field(description="Plain-English purpose, 1-2 sentences")
    sector: str = Field(description="Sector — e.g. local-government, NHS, education, justice")
    populations_affected: list[str] = Field(description="Groups whose rights could be affected")
    data_inputs: list[str] = Field(description="Categories of input data the system uses")
    data_outputs: list[str] = Field(description="Categories of output / decision the system produces")
    autonomy_level: str = Field(description="Level of autonomy: advisory, decision-support, automated, fully-autonomous")
    human_in_the_loop: bool = Field(description="Whether a human reviews every output before action")
    deployment_context: str = Field(description="On-prem / cloud / hybrid; UK/EU/US data residency")
    likely_annex_iii_categories: list[str] = Field(description="Annex III §1-§8 categories that may apply")
    risks_flagged: list[str] = Field(description="Known risks called out by the deployer")


class AIActClassification(BaseModel):
    risk_tier: str = Field(description="One of: prohibited, high-risk, limited-risk, minimal-risk, GPAI")
    annex_iii_match: list[str] = Field(description="Specific Annex III paragraphs matched, e.g. '§5(b) eligibility for public benefits'")
    article_5_concerns: list[str] = Field(description="Any practices that might trigger Article 5 prohibitions")
    article_6_rationale: str = Field(description="Why this is or isn't high-risk under Article 6")
    obligations_triggered: list[str] = Field(description="Articles 9-15 obligations, plus Article 27 FRIA if public-authority deployer")
    transparency_obligations: list[str] = Field(description="Article 50 transparency obligations if applicable (chatbots, deepfakes, etc.)")
    confidence: str = Field(description="HIGH / MEDIUM / LOW — confidence in this classification")
    review_required_by: str = Field(description="Role recommended to sign off — e.g. DPO, SIRO, named conformity assessor")
    rationale_summary: str = Field(description="2-4 sentence rationale a non-technical board can read")


# ── Stage 1 — Intake ──────────────────────────────────────────────────────

INTAKE_SYSTEM = textwrap.dedent("""\
    You are an EU AI Act compliance analyst working with a UK public-sector
    deployer (Local Authority, NHS Trust, Housing Association, central
    government department).

    Parse a plain-English description of an AI system and extract the
    structured information a Conformity Assessment Body or Information
    Governance officer needs to begin classification.

    Be precise. If a field is genuinely missing from the description, return
    a clearly-marked placeholder like "NOT STATED — ASK DEPLOYER".

    For likely_annex_iii_categories, only list paragraphs that look plausibly
    in scope from the description — be conservative; the classify step does
    the deeper work.

    Use British English throughout (organisation, programme, behaviour, etc.).
""")


def cmd_intake(args: argparse.Namespace) -> None:
    description = _read_text(args.description)
    ref = getattr(args, "request_id", None) or f"AIACT-{_hash(description)[:8]}"

    print(f"AI Act intake — analysing system description (ref={ref})…")
    result = _call_structured(
        INTAKE_SYSTEM,
        f"Parse the following AI system description:\n\n{description}",
        AIActIntake,
    )
    payload = result.model_dump()
    payload["__source_hash"] = _hash(description)
    payload["__source_excerpt"] = description[:600]
    payload["__request_id"] = ref
    payload["__ts"] = datetime.utcnow().isoformat() + "Z"

    cached = _save_intake(ref, payload)

    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2))
    else:
        body = (
            f"System: {payload['system_name']}\n"
            f"Deployer: {payload['deployer']}\n"
            f"Purpose: {payload['purpose']}\n"
            f"Sector: {payload['sector']}\n"
            f"Autonomy: {payload['autonomy_level']}\n"
            f"Human-in-the-loop: {payload['human_in_the_loop']}\n"
            f"Deployment: {payload['deployment_context']}\n\n"
            f"Populations affected:\n"
            + "\n".join(f"  - {p}" for p in payload["populations_affected"])
            + "\n\nData inputs:\n"
            + "\n".join(f"  - {d}" for d in payload["data_inputs"])
            + "\n\nData outputs:\n"
            + "\n".join(f"  - {d}" for d in payload["data_outputs"])
            + "\n\nLikely Annex III categories:\n"
            + "\n".join(f"  - {c}" for c in payload["likely_annex_iii_categories"])
            + "\n\nRisks the deployer has flagged:\n"
            + "\n".join(f"  - {r}" for r in payload["risks_flagged"])
            + f"\n\n→ Cached at: {cached}\n→ Reuse with: civiclaw aiact classify {args.description!r}\n→ Or: civiclaw aiact annex-iv --request-id {ref}\n"
        )
        _print_section(f"AI ACT INTAKE — ref {ref}", body)

    _audit.append(
        actor=ACTOR, skill="aiact", event="intake.parsed", ref=ref,
        data={
            "system_name": payload["system_name"],
            "deployer": payload["deployer"],
            "sector": payload["sector"],
            "source_hash": payload["__source_hash"],
        },
    )


# ── Stage 2 — Classify ────────────────────────────────────────────────────

CLASSIFY_SYSTEM = textwrap.dedent("""\
    You are a senior EU AI Act conformity assessor. Given a structured
    description of an AI system, classify it against the EU AI Act
    (Regulation 2024/1689).

    Risk tiers:

    1. **Prohibited** (Article 5) — social scoring by public authorities,
       real-time remote biometric ID in public spaces (with narrow
       exceptions), emotion recognition in workplace/education, untargeted
       facial-image scraping, etc.

    2. **High-risk** (Article 6 + Annex III) — Annex III lists 8 categories
       including: biometric categorisation; critical infrastructure; education
       and vocational training; employment, HR, workforce management;
       essential public services and benefits; law enforcement; migration,
       asylum and border control; administration of justice and democratic
       processes.

    3. **Limited risk** (Article 50) — chatbots, AI-generated content,
       deepfakes — transparency obligations only.

    4. **Minimal risk** — no specific obligations beyond voluntary codes.

    5. **GPAI** (general-purpose AI) — separate obligations under Articles 51-55,
       not the deployer's primary concern but worth flagging.

    Be PRECISE about Annex III matches — quote the paragraph and section.
    Be cautious — a public-sector AI assistant for benefits, housing, education,
    or essential services is almost always high-risk under §5.

    Return obligations_triggered as a list of Articles (9, 10, 11, 12, 13, 14,
    15, 27 etc.) that apply given the classification AND the deployer type
    (Article 27 FRIA applies to public-authority deployers).

    Use British English throughout.
""")


def cmd_classify(args: argparse.Namespace) -> None:
    description = _read_text(args.description)
    ref = f"AIACT-{_hash(description)[:8]}"

    print(f"AI Act classification — assessing risk tier (ref={ref})…")

    # Reuse intake if cached, else run intake silently first
    intake_path = INTAKE_CACHE / f"{ref}.json"
    if not intake_path.exists():
        intake_args = argparse.Namespace(description=args.description, request_id=ref, json_output=True)
        # Suppress intake's own stdout by capturing it
        from io import StringIO
        _stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            cmd_intake(intake_args)
        finally:
            sys.stdout = _stdout
    intake = _load_intake(ref)

    result = _call_structured(
        CLASSIFY_SYSTEM,
        f"Classify this AI system. Structured intake:\n\n{json.dumps(intake, indent=2)}\n\n"
        f"Original description:\n\n{description}",
        AIActClassification,
    )
    classification = result.model_dump()

    # Persist alongside intake so annex-iv / fria can read both
    intake["__classification"] = classification
    _save_intake(ref, intake)

    if getattr(args, "json_output", False):
        print(json.dumps(classification, indent=2))
    else:
        body = (
            f"Risk tier: **{classification['risk_tier'].upper()}**\n"
            f"Confidence: {classification['confidence']}\n"
            f"Sign-off recommended by: {classification['review_required_by']}\n\n"
            f"Article 6 rationale:\n{classification['article_6_rationale']}\n\n"
            f"Annex III matches:\n"
            + "\n".join(f"  - {m}" for m in classification["annex_iii_match"])
            + "\n\nArticle 5 (prohibited-practice) concerns:\n"
            + ("\n".join(f"  - {c}" for c in classification["article_5_concerns"]) if classification["article_5_concerns"] else "  (none)")
            + "\n\nObligations triggered:\n"
            + "\n".join(f"  - {o}" for o in classification["obligations_triggered"])
            + "\n\nArticle 50 transparency obligations:\n"
            + ("\n".join(f"  - {t}" for t in classification["transparency_obligations"]) if classification["transparency_obligations"] else "  (none)")
            + f"\n\nSummary for board:\n{classification['rationale_summary']}\n"
            + f"\n→ Reuse ref: civiclaw aiact annex-iv --request-id {ref}\n"
        )
        _print_section(f"AI ACT CLASSIFICATION — ref {ref}", body)

    _audit.append(
        actor=ACTOR, skill="aiact", event="risk.classified", ref=ref,
        data={
            "risk_tier": classification["risk_tier"],
            "confidence": classification["confidence"],
            "annex_iii_count": len(classification["annex_iii_match"]),
            "article_5_concerns": len(classification["article_5_concerns"]),
        },
    )


# ── Stage 3 — Annex IV technical documentation ───────────────────────────

ANNEX_IV_SYSTEM = textwrap.dedent("""\
    You are drafting Annex IV technical documentation for an EU AI Act
    high-risk system. Annex IV requires documentation across the following
    sections — produce ALL of them as Markdown:

    1. **General description** — purpose, version, description of how the
       system interacts with hardware and software it depends on.
    2. **Detailed description of system elements** — the methods, training
       data, validation/testing data, computational resources, design
       specifications, key design choices, system architecture diagram (as
       text), validation procedures, the cybersecurity measures.
    3. **Detailed information about the monitoring, functioning and control**
       of the AI system — capabilities, limitations, accuracy, robustness,
       expected output, foreseeable misuse, predetermined changes.
    4. **Risk management system per Article 9** — known risks, residual
       risks, risk-acceptance criteria, risk-treatment measures.
    5. **Data governance per Article 10** — training/validation/test data
       sources and quality, data preparation processes, examination of
       biases, data labelling.
    6. **Human oversight per Article 14** — measures the deployer takes to
       ensure human review, the named role(s) responsible, escalation paths.
    7. **Lifecycle and change management** — testing on each release,
       version control, the post-market monitoring plan.
    8. **Records of compliance** — copies of EU declaration of conformity,
       CE marking process, post-market monitoring outputs.

    Where the deployer has not supplied information for a section, write
    "**NOT YET DOCUMENTED — DEPLOYER TO PROVIDE**" with a 1-line prompt of
    what's missing. Do NOT fabricate content.

    Use British English. Cite specific Article and Annex paragraph numbers
    where they apply. Keep the tone factual and audit-ready.

    The deployer's audit log is produced by civiclaw's append-only chain —
    explicitly reference this in section 7 (post-market monitoring) as the
    Article 12 logging mechanism.
""")


def cmd_annex_iv(args: argparse.Namespace) -> None:
    ref = args.request_id
    intake = _load_intake(ref)
    classification = intake.get("__classification")
    if not classification:
        # Run classify silently first
        print(f"(no prior classification for {ref}; running classify…)")
        from io import StringIO
        _stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            cmd_classify(argparse.Namespace(
                description=intake.get("__source_excerpt", ""), json_output=True,
            ))
        finally:
            sys.stdout = _stdout
        intake = _load_intake(ref)
        classification = intake.get("__classification")

    if classification and classification.get("risk_tier", "").lower() != "high-risk":
        print(
            f"NOTE: classified as {classification.get('risk_tier')!r}. Annex IV "
            f"is only mandatory for high-risk systems. Continuing anyway because "
            f"voluntary documentation is good practice and the format is the same.",
            file=sys.stderr,
        )

    print(f"Drafting Annex IV technical documentation (ref={ref})…")
    user_prompt = (
        f"Draft full Annex IV technical documentation for the AI system below. "
        f"The deployer is a UK public-sector body. Use the structured intake "
        f"and classification context to fill every section faithfully; flag "
        f"missing items rather than inventing them.\n\n"
        f"Structured intake:\n{json.dumps(intake, indent=2)}\n\n"
        f"Classification:\n{json.dumps(classification, indent=2) if classification else '(unavailable)'}\n"
    )
    body = _call(ANNEX_IV_SYSTEM, user_prompt)
    body = (
        f"# Annex IV — Technical Documentation\n\n"
        f"**System ref:** `{ref}`\n"
        f"**Drafted:** {datetime.utcnow().isoformat()}Z\n"
        f"**Drafted by:** civiclaw aiact skill v0.1 (model: {MODEL})\n"
        f"**Status:** DRAFT — Article 14 oversight required before submission "
        f"(`civiclaw approve --ref {ref}`)\n\n"
        f"---\n\n"
        f"{body}\n"
    )
    path = _save_draft(ref, "annex-iv", body)
    print(f"Annex IV draft written to: {path}\n")
    _print_section("ANNEX IV — first page", body[:2000] + "\n…[truncated for terminal preview — full draft on disk]")

    _audit.append(
        actor=ACTOR, skill="aiact", event="annex_iv.drafted", ref=ref,
        data={"draft_path": str(path), "model": MODEL, "char_count": len(body)},
    )


# ── Stage 4 — Fundamental Rights Impact Assessment ───────────────────────

FRIA_SYSTEM = textwrap.dedent("""\
    You are drafting an Article 27 Fundamental Rights Impact Assessment (FRIA)
    for an EU AI Act high-risk system being deployed by a public authority.

    The FRIA is a deployer obligation (not a provider obligation) under
    Article 27. It must cover:

    1. **Purpose and intended use** — why the deployer is using the system,
       what decisions or actions it will support.
    2. **Period and frequency of use** — how often, how long, under what
       circumstances.
    3. **Categories of natural persons affected** — including especially
       vulnerable groups (children, adults at risk, ethnic minorities,
       people with disabilities, asylum seekers).
    4. **Specific risks of harm to fundamental rights** — name the rights
       (privacy, non-discrimination, dignity, fair process, freedom of
       expression, social security access, etc.) and the specific way
       this system could harm them.
    5. **Human oversight measures** — Article 14 measures, named roles,
       escalation paths, override capability.
    6. **Measures taken in case of materialisation of risks** — concrete
       mitigations the deployer will use if a harm is identified.
    7. **Internal governance and complaints mechanism** — how affected
       persons can raise concerns and obtain redress.
    8. **Notification to the market surveillance authority and to affected
       persons** — when and how.

    For UK public-sector deployers, also:
    - Cross-reference UK GDPR Article 22 (automated decision-making)
    - Note any overlap with the deployer's Equality Impact Assessment
    - Reference the relevant ICO Code of Practice

    Where the deployer has not yet provided information for a section,
    write "**NOT YET ASSESSED — DEPLOYER TO COMPLETE**" with a one-line
    prompt of what's needed. Do NOT fabricate.

    Use British English throughout. Cite specific Articles and paragraphs.
""")


def cmd_fria(args: argparse.Namespace) -> None:
    ref = args.request_id
    intake = _load_intake(ref)
    classification = intake.get("__classification")

    print(f"Drafting Fundamental Rights Impact Assessment (ref={ref})…")
    user_prompt = (
        f"Draft a complete FRIA (Article 27) for the AI system below. The "
        f"deployer is a UK public authority. Use the intake and classification "
        f"to populate every section; flag missing inputs rather than inventing.\n\n"
        f"Structured intake:\n{json.dumps(intake, indent=2)}\n\n"
        f"Classification:\n{json.dumps(classification, indent=2) if classification else '(unavailable)'}\n"
    )
    body = _call(FRIA_SYSTEM, user_prompt)
    body = (
        f"# Fundamental Rights Impact Assessment (FRIA)\n\n"
        f"**Statutory basis:** EU AI Act (Regulation 2024/1689) Article 27\n"
        f"**System ref:** `{ref}`\n"
        f"**Drafted:** {datetime.utcnow().isoformat()}Z\n"
        f"**Drafted by:** civiclaw aiact skill v0.1 (model: {MODEL})\n"
        f"**Status:** DRAFT — Article 14 oversight required before deployment "
        f"(`civiclaw approve --ref {ref}`)\n\n"
        f"---\n\n"
        f"{body}\n"
    )
    path = _save_draft(ref, "fria", body)
    print(f"FRIA draft written to: {path}\n")
    _print_section("FRIA — first page", body[:2000] + "\n…[truncated for terminal preview — full draft on disk]")

    _audit.append(
        actor=ACTOR, skill="aiact", event="fria.drafted", ref=ref,
        data={"draft_path": str(path), "model": MODEL, "char_count": len(body)},
    )


# ── CLI ───────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aiact", description="EU AI Act risk classification + Annex IV / FRIA generation.")
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("intake", help="Parse a system description into structured AI Act intake.")
    pi.add_argument("description", help="Path to a system description text file or the description text itself.")
    pi.add_argument("--json", dest="json_output", action="store_true", help="Print JSON instead of formatted text.")
    pi.set_defaults(func=cmd_intake)

    pc = sub.add_parser("classify", help="Classify the system against EU AI Act risk tiers.")
    pc.add_argument("description", help="Path to a system description text file or the description text itself.")
    pc.add_argument("--json", dest="json_output", action="store_true")
    pc.set_defaults(func=cmd_classify)

    pa = sub.add_parser("annex-iv", help="Generate Annex IV technical documentation.")
    pa.add_argument("--request-id", required=True, dest="request_id")
    pa.set_defaults(func=cmd_annex_iv)

    pf = sub.add_parser("fria", help="Generate Article 27 Fundamental Rights Impact Assessment.")
    pf.add_argument("--request-id", required=True, dest="request_id")
    pf.set_defaults(func=cmd_fria)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
