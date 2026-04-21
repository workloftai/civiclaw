#!/usr/bin/env python3
"""
civiclaw FOI skill — UK Freedom of Information Act 2000 request handling.

Four commands mirroring DSAR:
  intake     — parse a FOI request, qualify against s.1 FOIA, flag likely exemptions
  fee-check  — s.12 cost-limit assessment (£450 / 18 hours for LAs)
  search     — identify which departments likely hold the info
  respond    — draft the response letter, exemption rationale, PIT text, rights-to-appeal footer

Every stage writes to the civiclaw audit log so the full trail is EU AI Act
Art. 12-ready. `respond` is marked human_in_the_loop; the runtime expects a
`civiclaw approve --ref <id>` before the draft leaves the agent.
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
    ABSOLUTE_EXEMPTIONS,
    FEE_LIMIT_HOURS,
    FEE_LIMIT_POUNDS,
    FEE_STANDARD_RATE_PER_HOUR,
    MAX_TOKENS,
    MODEL,
    QUALIFIED_EXEMPTIONS,
    SAMPLE_REQUESTS,
)


AUDIT_PATH = _REPO_ROOT / ".audit" / "civiclaw.jsonl"
_audit = AuditLog(AUDIT_PATH)
ACTOR = os.environ.get("CIVICLAW_ACTOR", "anonymous")


def _actor() -> str:
    return ACTOR


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


def _format_exemptions() -> str:
    lines = ["ABSOLUTE EXEMPTIONS (no public-interest test required):"]
    for e in ABSOLUTE_EXEMPTIONS:
        note = f" — {e.get('notes','')}" if e.get("notes") else ""
        lines.append(f"  - {e['section']} {e['name']}{note}")
    lines.append("\nQUALIFIED EXEMPTIONS (public-interest test required):")
    for e in QUALIFIED_EXEMPTIONS:
        note = f" — {e.get('notes','')}" if e.get("notes") else ""
        lines.append(f"  - {e['section']} {e['name']}{note}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stage 1 — Intake
# ---------------------------------------------------------------------------

INTAKE_SYSTEM = textwrap.dedent(f"""\
    You are a UK Local Authority Information Governance Officer handling a
    new Freedom of Information Act 2000 request. You are decisively practical
    and legally precise.

    For the request provided, produce a concise structured analysis:

    1. **Qualification (s.1 FOIA 2000)**
       - Is it a valid request in writing?
       - Does it identify the information adequately for a reasonable search?
       - Is it for recorded information (not opinion, not future-dated plans)?
       - Does it request environmental information? If yes, route to the
         Environmental Information Regulations 2004 under s.39 FOIA.

    2. **Applicant handling**
       - Is there any indication of repeat / vexatious requests (s.14)?
       - Is there a clarification needed before the 20-working-day clock can
         start running?

    3. **Likely exemptions**
       - Scan the request against:
         {_format_exemptions()}
       - Identify the most probable exemptions and whether they are absolute
         or qualified.
       - For each likely qualified exemption, note the public-interest
         factors that would be weighed.

    4. **Search scope**
       - Suggest which council departments or systems likely hold the
         requested information.
       - Estimate the complexity.

    5. **Risks and flags**
       - Third-party personal data (s.40 FOIA + s.3 DPA 2018)
       - Commercial confidentiality (s.43)
       - Active legal / investigatory proceedings (s.30 / s.42)
       - Anything that could extend the 20-day deadline or trigger a refusal
         notice under s.17

    6. **Immediate next steps**
       - What to do today
       - What to do before day 7
       - What needs sign-off from the Head of Information Governance

    Be thorough but concise. This is an internal triage note — not a letter
    to the requester. Use UK spelling.
""")


def cmd_intake(args: argparse.Namespace) -> None:
    request_text = _read_text(args.request_text)
    ref = getattr(args, "request_id", None) or f"FOI-{_hash(request_text)[:8]}"
    print(f"Analysing FOI request ({ref})...")
    result = _call(INTAKE_SYSTEM, f"FOI request to analyse:\n\n{request_text}")
    _print_section(f"FOI INTAKE ANALYSIS — {ref}", result)
    _audit.append(
        actor=_actor(), skill="foi", event="intake.parsed", ref=ref,
        data={"source_length": len(request_text), "source_hash": _hash(request_text)},
    )


# ---------------------------------------------------------------------------
# Stage 2 — Fee-check (s.12)
# ---------------------------------------------------------------------------

FEE_CHECK_SYSTEM = textwrap.dedent(f"""\
    You are a UK Local Authority IG Officer assessing whether a FOI request
    can be refused under s.12 FOIA 2000 on cost grounds.

    Under the Fees Regulations 2004, a local authority may refuse a request
    if the cost of compliance would exceed £{FEE_LIMIT_POUNDS} (equivalent to
    {FEE_LIMIT_HOURS} hours at £{FEE_STANDARD_RATE_PER_HOUR}/hour).

    Time that CAN be counted toward the cost:
      - Determining whether the information is held
      - Locating / retrieving the information
      - Extracting the information from a document

    Time that CANNOT be counted:
      - Redaction / considering exemptions
      - Drafting the response letter

    Multiple related requests may be aggregated (Regulation 5) — flag if
    there is any evidence of request-splitting.

    For the request provided, produce:
      - A realistic time estimate per task (bullet list)
      - A total estimated time and cost
      - A verdict: "within limit" / "at risk" / "exceeds limit"
      - If exceeds: advise on the s.12 notice wording and any refinement
        options for the requester to bring it under the limit.
""")


def cmd_fee_check(args: argparse.Namespace) -> None:
    request_text = _read_text(args.request_text)
    ref = getattr(args, "request_id", None) or f"FOI-{_hash(request_text)[:8]}"
    print(f"Assessing s.12 cost limit ({ref})...")
    result = _call(FEE_CHECK_SYSTEM, f"Request to cost-assess:\n\n{request_text}")
    _print_section(f"s.12 COST-LIMIT ASSESSMENT — {ref}", result)
    _audit.append(
        actor=_actor(), skill="foi", event="fee_limit.assessed", ref=ref,
        data={"fee_limit_pounds": FEE_LIMIT_POUNDS, "fee_limit_hours": FEE_LIMIT_HOURS},
    )


# ---------------------------------------------------------------------------
# Stage 3 — Search
# ---------------------------------------------------------------------------

SEARCH_SYSTEM = textwrap.dedent("""\
    You are a UK Local Authority IG Officer planning an FOI search.

    Given a request, map it to the likely departments and systems within a
    typical unitary / county / borough council that would hold the
    requested information. Examples of common targets:

      - Finance / procurement (for spend and contract questions)
      - Legal / democratic services (for committee papers, decisions)
      - HR (for staff-related questions, with s.40 exemptions noted)
      - Planning (for applications, enforcement)
      - Highways / Transport
      - Housing / Homelessness
      - Education / Children's Services
      - Adults Social Care
      - Environmental Health
      - ICT (for system-level data)

    For each department likely to hold relevant information:
      - **Relevance**: HIGH / MEDIUM / LOW
      - **Rationale**
      - **Systems to search** (e.g. SAP, Civica, Capita One, SharePoint)
      - **Estimated effort** in hours

    End with a prioritised search plan and total estimated hours.
""")


def cmd_search(args: argparse.Namespace) -> None:
    request_text = _read_text(args.request_text)
    ref = getattr(args, "request_id", None) or f"FOI-{_hash(request_text)[:8]}"
    print(f"Planning FOI search ({ref})...")
    result = _call(SEARCH_SYSTEM, f"Request:\n\n{request_text}")
    _print_section(f"FOI SEARCH PLAN — {ref}", result)
    _audit.append(
        actor=_actor(), skill="foi", event="search.planned", ref=ref,
        data={"source_hash": _hash(request_text)},
    )


# ---------------------------------------------------------------------------
# Stage 4 — Respond
# ---------------------------------------------------------------------------

RESPOND_SYSTEM = textwrap.dedent("""\
    You are a UK Local Authority Information Governance Officer drafting a
    formal response to a Freedom of Information Act 2000 request.

    Your draft must include:

    1. Header — council name (use "[Council Name]" placeholder), reference
       number, date, applicant's name.
    2. Acknowledgement — confirm receipt, reference s.1(1)(a) of FOIA for
       confirming whether the information is held.
    3. Disclosure — for each part of the request, either:
         (a) disclose the information clearly, or
         (b) refuse under a named exemption, citing the section, whether
             absolute or qualified, and (for qualified) a documented
             public-interest test reasoning in prose.
    4. Cost / s.12 notice — if applicable.
    5. s.40 carve-out — if any personal data of third parties is withheld,
       state this plainly and cite the relevant UK GDPR lawful basis.
    6. Environmental information routing — if s.39 applies, explain the
       switch to EIR 2004.
    7. Internal review and ICO rights — the mandatory rights-to-appeal
       footer: request an internal review within 40 working days; then
       escalate to the Information Commissioner at ico.org.uk.
    8. Tone — professional, neutral, readable. Assume the applicant may
       publish the response verbatim.

    The letter should be ready to send with minimal editing.
""")


def cmd_respond(args: argparse.Namespace) -> None:
    req = SAMPLE_REQUESTS.get(args.request_id)
    if not req:
        available = ", ".join(SAMPLE_REQUESTS.keys())
        print(f"ERROR: Request ID '{args.request_id}' not found. Available: {available}", file=sys.stderr)
        sys.exit(1)

    user_prompt = (
        f"Request reference: {req['id']}\n"
        f"Date received: {req['date_received']}\n"
        f"Deadline: {req['deadline']}\n"
        f"Today: {datetime.now().strftime('%d %B %Y')}\n"
        f"Applicant: {req['requester_name']}\n\n"
        f"Request text:\n{req['request_text']}\n\n"
        f"Topics: {', '.join(req['topics'])}\n"
        f"Exemptions considered: {', '.join(req['likely_exemptions_considered'])}\n"
        f"Estimated hours: {req['estimated_hours']}\n"
        f"Estimated cost: £{req['estimated_cost']}\n"
    )
    print(f"Drafting FOI response for {args.request_id}...")
    result = _call(RESPOND_SYSTEM, user_prompt)
    _print_section(f"FOI RESPONSE LETTER — {args.request_id}", result)
    _audit.append(
        actor=_actor(), skill="foi", event="response.drafted", ref=args.request_id,
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
        prog="civiclaw foi",
        description="UK FOIA 2000 request handling — intake, fee-check, search, respond.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_intake = sub.add_parser("intake", help="Parse an FOI request and flag likely exemptions.")
    p_intake.add_argument("request_text", help="FOI request text or path to .txt file.")
    p_intake.add_argument("--request-id", help="Optional reference ID (auto-generated if omitted).")
    p_intake.set_defaults(fn=cmd_intake)

    p_fee = sub.add_parser("fee-check", help="Assess s.12 cost limit for the request.")
    p_fee.add_argument("request_text", help="FOI request text or path to .txt file.")
    p_fee.add_argument("--request-id", help="Optional reference ID.")
    p_fee.set_defaults(fn=cmd_fee_check)

    p_search = sub.add_parser("search", help="Plan the internal search across council departments.")
    p_search.add_argument("request_text", help="FOI request text or path to .txt file.")
    p_search.add_argument("--request-id", help="Optional reference ID.")
    p_search.set_defaults(fn=cmd_search)

    p_resp = sub.add_parser("respond", help="Draft the FOI response letter.")
    p_resp.add_argument("--request-id", required=True, help="Reference ID, e.g. FOI-2026-001.")
    p_resp.set_defaults(fn=cmd_respond)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
