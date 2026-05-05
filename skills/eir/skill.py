#!/usr/bin/env python3
"""
civiclaw EIR skill — UK Environmental Information Regulations 2004 request handling.

Four commands (parallel to the foi skill, but applying the EIR regime):
  intake            — confirm Reg 5(1) qualification + Reg 2(1) "environmental information" boundary
  exception-check   — Reg 12 / Reg 13 analysis with the mandatory public-interest test
  search            — plan which council departments + systems likely hold the info
  respond           — draft the response letter, exception rationale, PIT prose, rights-to-appeal footer

Every stage writes to the civiclaw audit chain. `respond` is human-in-the-loop;
the runtime expects `civiclaw approve --ref <id>` before the draft leaves the agent.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import textwrap
from datetime import datetime
from pathlib import Path

import anthropic

# Wire to civiclaw runtime.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.audit import AuditLog  # noqa: E402

from config import (  # noqa: E402
    MAX_TOKENS,
    MODEL,
    REG_12_EXCEPTIONS,
    REG_13_GUIDANCE,
    REG_7_EXTENSION_WORKING_DAYS,
    SAMPLE_REQUESTS,
    STATUTORY_DEADLINE_WORKING_DAYS,
)


AUDIT_PATH = _REPO_ROOT / ".audit" / "civiclaw.jsonl"
_audit = AuditLog(AUDIT_PATH)
ACTOR = os.environ.get("CIVICLAW_ACTOR", "anonymous")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _client() -> anthropic.Anthropic:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("ERROR: ANTHROPIC_API_KEY not set.")
    return anthropic.Anthropic(api_key=key)


def _call(system: str, user: str) -> str:
    resp = _client().messages.create(
        model=MODEL, max_tokens=MAX_TOKENS, system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text  # type: ignore[attr-defined]


def _print_section(title: str, body: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    print(body)
    print()


def _read_text(text_or_path: str) -> str:
    p = Path(text_or_path)
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return text_or_path


def _format_exceptions() -> str:
    lines = ["EIR EXCEPTIONS — Reg 12 (all qualified, public-interest test required for every refusal):"]
    for e in REG_12_EXCEPTIONS:
        note = f" — {e.get('notes','')}" if e.get("notes") else ""
        lines.append(f"  - {e['reg']} {e['name']}{note}")
    lines.append("")
    lines.append("Reg 13 — personal data:")
    lines.append(f"  {REG_13_GUIDANCE}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stage 1 — Intake
# ---------------------------------------------------------------------------

INTAKE_SYSTEM = textwrap.dedent(f"""\
    You are a UK Local Authority Information Governance Officer triaging a
    new request under the Environmental Information Regulations 2004 (EIR).

    Be decisively practical and legally precise. Use British English.

    Produce a structured analysis covering:

    1. **Qualification (Reg 5(1) EIR + Reg 2(1) definition of "environmental
       information")**
       - Is the requested information environmental within the meaning of
         Reg 2(1)? Be explicit about which limb of the definition applies
         (state of elements / factors / measures / reports / cost-benefit /
         human health insofar as affected by environmental conditions).
       - If the request is mixed (some environmental, some not), explain the
         routing — environmental parts under EIR; non-environmental parts
         under FOIA s.39 routing.
       - Note that EIR allows ORAL requests too — confirm the form here.

    2. **Applicant handling**
       - Any indication of repeat / vexatious requests (Reg 12(4)(b))?
       - Any clarification needed before the {STATUTORY_DEADLINE_WORKING_DAYS}-working-day
         clock can start running (Reg 9 — duty to provide advice and assistance)?

    3. **Likely Reg 12 / Reg 13 exceptions**
       - Scan against:
{_format_exceptions()}
       - Identify the most probable exceptions and outline the public-interest
         factors a Council would weigh under Reg 12(1)(b). Remember the
         Reg 12(2) presumption in favour of disclosure.

    4. **Reg 7 extension**
       - Is this likely to be a complex/voluminous request that needs the
         extra {REG_7_EXTENSION_WORKING_DAYS} working days under Reg 7? If yes, draft a one-line
         placeholder for the Reg 7 notice text.

    5. **Search scope**
       - Which council departments / systems likely hold the information.
       - Estimate of complexity.

    6. **Risks and flags**
       - Personal data of third parties (Reg 13)
       - Commercial confidentiality (Reg 12(5)(e))
       - Active legal / investigatory proceedings (Reg 12(5)(b))
       - Any factor that could trigger a Reg 14 refusal notice

    7. **Immediate next steps**
       - Today / before day 7 / sign-off level required

    Be thorough but concise. This is an internal triage note — not the letter.
""")


def cmd_intake(args: argparse.Namespace) -> None:
    request_text = _read_text(args.request_text)
    ref = getattr(args, "request_id", None) or f"EIR-{_hash(request_text)[:8]}"
    print(f"Analysing EIR request ({ref})...")
    result = _call(INTAKE_SYSTEM, f"EIR request to analyse:\n\n{request_text}")
    _print_section(f"EIR INTAKE ANALYSIS — {ref}", result)
    _audit.append(
        actor=ACTOR, skill="eir", event="intake.parsed", ref=ref,
        data={"source_length": len(request_text), "source_hash": _hash(request_text)},
    )


# ---------------------------------------------------------------------------
# Stage 2 — Exception check
# ---------------------------------------------------------------------------

EXCEPTION_SYSTEM = textwrap.dedent(f"""\
    You are a UK Local Authority IG Officer running the Reg 12 / Reg 13
    exception analysis on an EIR request.

    Three rules to keep in mind on every output:

    1. ALL EIR exceptions are qualified — every refusal requires a
       public-interest test (PIT) at Reg 12(1)(b).
    2. Reg 12(2) embeds a presumption in favour of disclosure that must be
       explicitly weighed.
    3. There is no s.12-style cost refusal under EIR. A request cannot be
       refused for cost; it can only be subject to a "reasonable" charge
       under Reg 8 (rare in practice for routine LA requests).

    For each Reg 12 / Reg 13 exception that may apply, produce a structured
    block:

      - **Exception**: e.g. "Reg 12(5)(b) — Course of justice"
      - **Why this might apply** (1-2 sentences)
      - **Strength of engagement**: STRONG / MEDIUM / WEAK
      - **Public-interest factors FOR disclosure** (bulleted)
      - **Public-interest factors AGAINST disclosure** (bulleted)
      - **Provisional balance**: tentative — frames the IG officer's working
        view, not the final decision
      - **Evidence the IG team needs to substantiate the position** (e.g.
        "minute the Monitoring Officer's view on prejudice")

    End with a short recommended-position summary covering: which parts of
    the request are likely to be released, which are likely to be partially
    or wholly withheld, and the working public-interest balance.

    Use British English. Be precise about regulation citations.

    Reference list of exceptions:
{_format_exceptions()}
""")


def cmd_exception_check(args: argparse.Namespace) -> None:
    request_text = _read_text(args.request_text)
    ref = getattr(args, "request_id", None) or f"EIR-{_hash(request_text)[:8]}"
    print(f"Assessing Reg 12 / Reg 13 exceptions ({ref})...")
    result = _call(EXCEPTION_SYSTEM, f"EIR request to assess:\n\n{request_text}")
    _print_section(f"EIR EXCEPTION ANALYSIS — {ref}", result)
    _audit.append(
        actor=ACTOR, skill="eir", event="exceptions.assessed", ref=ref,
        data={"reg_12_exceptions_considered": [e["reg"] for e in REG_12_EXCEPTIONS]},
    )


# ---------------------------------------------------------------------------
# Stage 3 — Search
# ---------------------------------------------------------------------------

SEARCH_SYSTEM = textwrap.dedent("""\
    You are a UK Local Authority IG Officer planning the search for an EIR
    request. Map the request to the council departments and systems likely
    to hold environmental information. Common targets:

      - Environmental Health (air quality, contamination, noise, statutory nuisance)
      - Planning + Building Control (applications, conditions, enforcement, EIA documents)
      - Highways / Transport (LTPs, schemes, traffic counts, emissions modelling)
      - Climate Change / Sustainability team
      - Public Health (insofar as environmental conditions affect human health)
      - Parks + Open Spaces / Ecology + Biodiversity team
      - Waste Management
      - Flood Risk / Drainage
      - Property + Asset Management (for council estate emissions)
      - Cabinet Office / Democratic Services (for Cabinet papers, Members' briefings)

    For each department likely to hold relevant information:
      - Relevance: HIGH / MEDIUM / LOW
      - Rationale
      - Systems to search (e.g. AQMesh, Defra UK-AIR, Uniform/Idox, ESRI ArcGIS, SharePoint)
      - Estimated effort in hours

    End with a prioritised search plan and total estimated hours.
""")


def cmd_search(args: argparse.Namespace) -> None:
    request_text = _read_text(args.request_text)
    ref = getattr(args, "request_id", None) or f"EIR-{_hash(request_text)[:8]}"
    print(f"Planning EIR search ({ref})...")
    result = _call(SEARCH_SYSTEM, f"EIR request:\n\n{request_text}")
    _print_section(f"EIR SEARCH PLAN — {ref}", result)
    _audit.append(
        actor=ACTOR, skill="eir", event="search.planned", ref=ref,
        data={"approach": "department_mapping"},
    )


# ---------------------------------------------------------------------------
# Stage 4 — Respond
# ---------------------------------------------------------------------------

RESPOND_SYSTEM = textwrap.dedent("""\
    You are a UK Local Authority Information Governance Officer drafting a
    formal response to a request under the Environmental Information
    Regulations 2004.

    Your draft must include:

    1. **Header** — council name (use "[Council Name]" placeholder),
       reference number, date, applicant's name.

    2. **Acknowledgement** — confirm receipt; cite Reg 5(1) EIR. State the
       statutory deadline (20 working days from receipt) or, if a Reg 7
       extension is being applied, the new deadline (up to 40 working days)
       and the reason.

    3. **Confirmation of regime** — explicitly confirm the request is being
       handled under EIR 2004 because the information is environmental within
       the meaning of Reg 2(1). If part of the request is non-environmental,
       explain the FOIA s.39 routing and the parallel response.

    4. **Disclosure (per part of the request)** — for each part:
         (a) disclose the information clearly, with the format and any
             quality-assurance caveats; or
         (b) refuse under a named Reg 12 / Reg 13 exception, citing the
             regulation, summarising the public-interest test reasoning in
             prose (factors for, factors against, balance), and noting the
             Reg 12(2) presumption in favour of disclosure.

    5. **Reg 13 / personal data carve-out** — if any personal data of third
       parties is withheld, state plainly and cite the relevant UK GDPR
       lawful basis.

    6. **Reg 8 charging** — if any "reasonable charge" applies (rare for
       routine requests), state the basis, calculation and how to pay. If
       no charge applies, omit.

    7. **Internal review and ICO rights** — the mandatory rights-to-appeal
       footer: request internal review within 40 working days; then escalate
       to the Information Commissioner at ico.org.uk.

    8. **Tone** — professional, neutral, readable. Assume the applicant may
       publish the response verbatim (campaign groups and journalists often
       do). Use British English.

    The letter should be ready to send with minimal editing.
""")


def cmd_respond(args: argparse.Namespace) -> None:
    req = SAMPLE_REQUESTS.get(args.request_id)
    if not req:
        available = ", ".join(SAMPLE_REQUESTS.keys()) or "(none)"
        print(f"ERROR: Request ID {args.request_id!r} not found. Available: {available}", file=sys.stderr)
        sys.exit(1)

    user_prompt = (
        f"Request reference: {req['id']}\n"
        f"Date received: {req['date_received']}\n"
        f"Statutory deadline: {req['deadline']}\n"
        f"Today: {datetime.now().strftime('%d %B %Y')}\n"
        f"Applicant: {req['requester_name']}\n\n"
        f"Request text:\n{req['request_text']}\n\n"
        f"Topics: {', '.join(req['topics'])}\n"
        f"Exceptions considered: {', '.join(req['likely_exceptions_considered'])}\n"
    )
    print(f"Drafting EIR response for {args.request_id}...")
    result = _call(RESPOND_SYSTEM, user_prompt)
    _print_section(f"EIR RESPONSE LETTER — {args.request_id}", result)
    _audit.append(
        actor=ACTOR, skill="eir", event="response.drafted", ref=args.request_id,
        data={
            "word_count": len(result.split()),
            "requires_human_signoff": True,
            "draft_hash": _hash(result),
        },
    )
    print(
        "\n[civiclaw] Article 14 human-in-the-loop gate: "
        "this draft MUST be reviewed and approved before sending. "
        f"Run `civiclaw approve --ref {args.request_id}` to log the sign-off."
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="civiclaw eir",
        description="UK EIR 2004 request handling — intake, exception-check, search, respond.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_intake = sub.add_parser("intake", help="Parse an EIR request and qualify against Reg 2(1) / Reg 5(1).")
    p_intake.add_argument("request_text", help="EIR request text or path to .txt file.")
    p_intake.add_argument("--request-id", help="Optional reference ID.")
    p_intake.set_defaults(fn=cmd_intake)

    p_excp = sub.add_parser("exception-check", help="Assess Reg 12 / Reg 13 exceptions and run the public-interest test.")
    p_excp.add_argument("request_text", help="EIR request text or path to .txt file.")
    p_excp.add_argument("--request-id", help="Optional reference ID.")
    p_excp.set_defaults(fn=cmd_exception_check)

    p_search = sub.add_parser("search", help="Plan the internal search across council departments.")
    p_search.add_argument("request_text", help="EIR request text or path to .txt file.")
    p_search.add_argument("--request-id", help="Optional reference ID.")
    p_search.set_defaults(fn=cmd_search)

    p_resp = sub.add_parser("respond", help="Draft the EIR response letter.")
    p_resp.add_argument("--request-id", required=True, help="Reference ID, e.g. EIR-2026-001.")
    p_resp.set_defaults(fn=cmd_respond)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
