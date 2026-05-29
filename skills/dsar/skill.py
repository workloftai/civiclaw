#!/usr/bin/env python3
"""
Workloft DSAR Agent — UK GDPR Subject Access Request processor.

A CLI tool that assists Local Authority information governance teams with
the intake, search, redaction, and response stages of a Data Subject
Access Request (DSAR).

Usage:
    python3 dsar.py intake  "<request text or path to .txt file>"
    python3 dsar.py search  "<data subject name>"
    python3 dsar.py redact  <document.txt> --subject "<data subject name>"
    python3 dsar.py respond --request-id <REQ_ID>

Requires ANTHROPIC_API_KEY in the environment.
"""

import argparse
import hashlib
import json
import os
import sys
import textwrap
from datetime import datetime, timedelta
from pathlib import Path

import anthropic
import instructor
from pydantic import BaseModel, Field
from typing import Optional

# Wire to civiclaw runtime. Skill lives at skills/dsar/skill.py; repo root is two up.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.audit import AuditLog  # noqa: E402

from config import DATA_SOURCES, MODEL, MAX_TOKENS, SAMPLE_REQUESTS

# Audit log lives under .audit/ at the repo root so it's gitignored by default.
AUDIT_PATH = _REPO_ROOT / ".audit" / "civiclaw.jsonl"
_audit = AuditLog(AUDIT_PATH)
ACTOR = os.environ.get("CIVICLAW_ACTOR", "anonymous")


def _actor() -> str:
    return ACTOR


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Structured output models
# ---------------------------------------------------------------------------

class DSARIntake(BaseModel):
    requester_name: str = Field(description="Name of the person submitting the request")
    data_subject: str = Field(description="Name of the person whose data is requested")
    relationship: str = Field(description="Requester's relationship to data subject")
    scope: str = Field(description="What data is being requested, in plain English")
    data_categories: list[str] = Field(description="Specific types of data requested")
    identity_verified: bool = Field(description="Whether proof of identity was provided")
    authority_demonstrated: bool = Field(description="Whether authority to request on behalf of subject is shown")
    date_of_birth: Optional[str] = Field(default=None, description="Data subject's DOB if provided")
    contact_email: Optional[str] = Field(default=None)
    contact_phone: Optional[str] = Field(default=None)
    contact_address: Optional[str] = Field(default=None)
    urgency_flags: list[str] = Field(default_factory=list, description="Legal proceedings, complaints, tight deadlines")
    recommended_next_steps: list[str] = Field(description="What the IG team should do first")
    risks_and_blockers: list[str] = Field(description="Anything that could delay the request")


class DataSourceRelevance(BaseModel):
    source_id: str
    source_name: str
    relevance: str = Field(description="HIGH, MEDIUM, LOW, or NONE")
    rationale: str
    action_required: str
    estimated_records: str


class SearchResult(BaseModel):
    subject_name: str
    sources: list[DataSourceRelevance]
    total_estimated_effort_days: float
    priority_search_order: list[str] = Field(description="Source IDs in order of priority")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _have_anthropic() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _client() -> anthropic.Anthropic:
    """Return an Anthropic client, failing fast if the key is missing."""
    if not _have_anthropic():
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _instructor_client():
    """Return an Instructor-wrapped client for structured outputs.

    Structured outputs depend on Anthropic's tool-use schema; sovereign-mode (Ollama)
    is not wired here yet. Plain-text `_call()` does fall back to the router.
    """
    if not _have_anthropic():
        print(
            "ERROR: structured-output stages (e.g. dsar intake) currently require ANTHROPIC_API_KEY.\n"
            "Sovereign-mode (Ollama) supports plain-text stages only — see core/router.py.",
            file=sys.stderr,
        )
        sys.exit(1)
    return instructor.from_anthropic(_client())


def _call(system: str, user: str) -> str:
    """Send a single-turn message and return the text response.

    Falls back to the sovereign router (Ollama/Qwen) when no Anthropic key is set,
    so plain-text DSAR stages (search/redact/respond) run end-to-end on-prem.
    """
    if _have_anthropic() and os.environ.get("CIVICLAW_MODEL") != "ollama":
        client = _client()
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text
    from core.router import chat_text
    return chat_text(system, user, model_tier="mid", max_tokens=MAX_TOKENS)


def _call_structured(system: str, user: str, response_model):
    """Send a message and get back a structured Pydantic model."""
    client = _instructor_client()
    return client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
        response_model=response_model,
    )


def _print_section(title: str, body: str) -> None:
    """Pretty-print a titled section to stdout."""
    rule = "=" * 72
    print(f"\n{rule}")
    print(f"  {title}")
    print(rule)
    print(body)
    print()


def _read_text(text_or_path: str) -> str:
    """If text_or_path is a readable file, return its contents; otherwise
    return the string as-is."""
    p = Path(text_or_path)
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return text_or_path


# ---------------------------------------------------------------------------
# Stage 1 — Intake
# ---------------------------------------------------------------------------

INTAKE_SYSTEM = textwrap.dedent("""\
    You are a UK GDPR Data Subject Access Request (DSAR) intake analyst
    working for a Local Authority information governance team.

    Your job is to parse an incoming DSAR and extract structured information.
    You must identify:

    1. **Requester name** — the person submitting the request.
    2. **Data subject** — the person whose data is being requested (may be the
       same as the requester, or a child/dependant).
    3. **Relationship** — how the requester relates to the data subject
       (self, parent, legal guardian, solicitor, etc.).
    4. **Scope** — what data is being requested, in plain English.
    5. **Specific data categories** — list the specific types of data requested
       (education records, social care records, health records, etc.).
    6. **Identity verification status** — whether proof of identity has been
       provided, mentioned, or is missing.
    7. **Parental responsibility / authority** — whether the requester has
       demonstrated authority to request data on behalf of the subject.
    8. **Date of birth** — of the data subject, if provided.
    9. **Contact details** — any email, phone, or postal address provided.
    10. **Urgency flags** — any mention of legal proceedings, complaints,
        or tight deadlines.
    11. **Recommended next steps** — what the IG team should do first.

    Respond in a clear, structured format using markdown headings.
    Be precise and professional. Flag anything that could delay the request
    (e.g., missing ID, unclear scope, potential exemptions).
""")


def cmd_intake(args: argparse.Namespace) -> None:
    """Parse a DSAR request and extract key information."""
    request_text = _read_text(args.request_text)
    ref = getattr(args, 'request_id', None) or f"REQ-{_hash(request_text)[:8]}"
    print("Analysing DSAR request...")

    if getattr(args, 'json_output', False):
        result = _call_structured(
            INTAKE_SYSTEM,
            f"Parse the following DSAR request:\n\n{request_text}",
            DSARIntake,
        )
        import json as json_mod
        print(json_mod.dumps(result.model_dump(), indent=2))
        data = result.model_dump()
    else:
        result_text = _call(INTAKE_SYSTEM, f"Parse the following DSAR request:\n\n{request_text}")
        _print_section("DSAR INTAKE ANALYSIS", result_text)
        data = {"summary_chars": len(result_text), "source_hash": _hash(request_text)}

    _audit.append(
        actor=_actor(), skill="dsar", event="intake.parsed", ref=ref,
        data={"source_length": len(request_text), **data},
    )


# ---------------------------------------------------------------------------
# Stage 2 — Search
# ---------------------------------------------------------------------------

SEARCH_SYSTEM = textwrap.dedent("""\
    You are a UK Local Authority data search specialist. Given a data
    subject's name and a list of the Council's data systems, you must
    determine which systems are likely to hold personal data about the
    subject.

    For each system, provide:
    - **Relevance**: HIGH / MEDIUM / LOW / NONE
    - **Rationale**: Why this system may or may not hold data
    - **Action required**: What search the IG team should perform
    - **Estimated records**: A rough estimate of document volume
    - **Retention note**: Whether records may have been destroyed

    Consider the subject's likely interactions with council services based
    on their profile (age, context provided).

    End with a prioritised search plan listing the systems in order of
    likely relevance, and an estimated total effort in working days.

    Be thorough — missing a data source is a compliance risk.
""")


def cmd_search(args: argparse.Namespace) -> None:
    """Identify which LA data sources likely hold the subject's data."""
    subject = args.subject_name
    sources_description = "\n".join(
        f"- **{s['id']}** — {s['name']}: {s['description']} "
        f"(Retention: {s['retention_years']} years, Controller: {s['controller']})"
        for s in DATA_SOURCES
    )
    user_prompt = (
        f"Data subject: {subject}\n\n"
        f"Council data systems:\n{sources_description}\n\n"
        f"Identify which systems are likely to hold data about this subject "
        f"and recommend a search plan."
    )
    print(f"Searching for data sources relating to: {subject}...")
    result = _call(SEARCH_SYSTEM, user_prompt)
    _print_section(f"DATA SOURCE SEARCH — {subject}", result)
    _audit.append(
        actor=_actor(), skill="dsar", event="search.planned", ref=f"SUB-{_hash(subject)[:8]}",
        data={"subject": subject, "systems_considered": [s["id"] for s in DATA_SOURCES]},
    )


# ---------------------------------------------------------------------------
# Stage 3 — Redaction
# ---------------------------------------------------------------------------

REDACT_SYSTEM = textwrap.dedent("""\
    You are a UK GDPR redaction specialist working for a Local Authority.
    You are preparing documents for disclosure under a Subject Access
    Request (SAR).

    The data subject is entitled to their own personal data. However, you
    MUST redact personal data belonging to third parties (people other
    than the data subject) unless:
    - The third party has consented to disclosure, or
    - It is reasonable to disclose without consent.

    For each third party mentioned in the document, redact:
    - Full names → [REDACTED — Third Party Name]
    - Addresses → [REDACTED — Third Party Address]
    - Phone numbers → [REDACTED — Third Party Phone]
    - Email addresses → [REDACTED — Third Party Email]
    - Any other identifying details

    DO NOT redact:
    - The data subject's own personal data
    - Job titles or roles (e.g., "Head Teacher", "SENCO") — these are not
      personal data when used generically
    - Organisation names (e.g., school names, NHS trusts)
    - The data subject's parent/guardian details IF they are the requester

    Professional names (teachers, social workers, doctors, etc.) who are
    acting in their professional capacity SHOULD be redacted unless there
    is a clear reason to disclose (e.g., the subject needs to know who
    made a decision about them). Use your judgement and flag borderline
    cases.

    Return the FULL document with redactions applied. After the document,
    provide a "Redaction Log" listing every redaction made, the original
    text, the reason, and the legal basis (typically UK GDPR Art. 15(4)).
""")


def cmd_redact(args: argparse.Namespace) -> None:
    """Redact third-party personal data from a document."""
    doc_path = Path(args.document)
    if not doc_path.is_file():
        print(f"ERROR: File not found: {doc_path}", file=sys.stderr)
        sys.exit(1)

    document_text = doc_path.read_text(encoding="utf-8")
    subject = args.subject
    requester = args.requester or None

    user_prompt = f"Data subject: {subject}\n"
    if requester:
        user_prompt += f"Requester (do not redact): {requester}\n"
    user_prompt += f"\nDocument to redact:\n\n{document_text}"

    print(f"Redacting third-party data from: {doc_path.name}")
    print(f"Data subject (preserve): {subject}")
    if requester:
        print(f"Requester (preserve): {requester}")

    result = _call(REDACT_SYSTEM, user_prompt)
    _print_section(f"REDACTED DOCUMENT — {doc_path.name}", result)

    # Save redacted version
    out_path = doc_path.with_stem(doc_path.stem + "_redacted")
    out_path.write_text(result, encoding="utf-8")
    print(f"Redacted document saved to: {out_path}")
    _audit.append(
        actor=_actor(), skill="dsar", event="redaction.applied",
        ref=f"DOC-{_hash(str(doc_path))[:8]}",
        data={
            "document": doc_path.name,
            "pre_hash": _hash(document_text),
            "post_hash": _hash(result),
            "subject": subject,
            "requester": requester,
        },
    )


# ---------------------------------------------------------------------------
# Stage 4 — Response drafting
# ---------------------------------------------------------------------------

RESPOND_SYSTEM = textwrap.dedent("""\
    You are a UK Local Authority Information Governance Officer drafting a
    formal response to a Data Subject Access Request (DSAR) under Article 15
    of the UK GDPR and Part 3/4 of the Data Protection Act 2018.

    Draft a professional, legally compliant response letter that includes:

    1. **Header** — Council name (use "[Council Name]" as placeholder),
       reference number, date.
    2. **Acknowledgement** — Confirm the request was received and the
       legal basis for the response.
    3. **Scope confirmation** — Restate what data was requested.
    4. **Search summary** — Which systems were searched.
    5. **Disclosure** — How many documents are enclosed, in what format.
    6. **Redactions** — Explain any redactions made (third-party data under
       Art. 15(4) UK GDPR) and cite the legal basis.
    7. **Exemptions** — List any exemptions applied (if any) with legal
       references.
    8. **Rights reminder** — Inform the requester of their right to
       complain to the ICO (Information Commissioner's Office) and the
       council's own complaints process.
    9. **Contact details** — DPO contact information (use placeholder).
    10. **Tone** — Professional, empathetic, clear. Avoid jargon where
        possible. This letter may be read by a concerned parent.

    The letter should be ready to print and send with minimal editing.
""")


def cmd_respond(args: argparse.Namespace) -> None:
    """Draft a DSAR response letter for a given request."""
    req_id = args.request_id
    req = SAMPLE_REQUESTS.get(req_id)
    if not req:
        available = ", ".join(SAMPLE_REQUESTS.keys())
        print(f"ERROR: Request ID '{req_id}' not found. Available: {available}", file=sys.stderr)
        sys.exit(1)

    # Build context for the AI
    sources_searched = [
        s for s in DATA_SOURCES if s["id"] in req["sources_searched"]
    ]
    sources_text = "\n".join(
        f"- {s['name']} ({s['controller']})" for s in sources_searched
    )

    user_prompt = (
        f"Draft a DSAR response letter with the following details:\n\n"
        f"Request reference: {req['id']}\n"
        f"Date received: {req['date_received']}\n"
        f"Response deadline: {req['deadline']}\n"
        f"Today's date: {datetime.now().strftime('%d %B %Y')}\n\n"
        f"Requester: {req['requester_name']} ({req['requester_relationship']})\n"
        f"Data subject: {req['data_subject']} (DOB: {req['dob']})\n"
        f"Scope: {req['scope']}\n\n"
        f"Identity verified: {'Yes' if req['identity_verified'] else 'No'}\n"
        f"Authority verified: {'Yes' if req['authority_verified'] else 'No'}\n\n"
        f"Systems searched:\n{sources_text}\n\n"
        f"Documents found: {req['documents_found']}\n"
        f"Documents redacted: {req['documents_redacted']}\n"
        f"Exemptions applied: {', '.join(req['exemptions_applied']) or 'None'}\n"
    )

    print(f"Drafting response for request: {req_id}...")
    result = _call(RESPOND_SYSTEM, user_prompt)
    _print_section(f"DSAR RESPONSE LETTER — {req_id}", result)
    _audit.append(
        actor=_actor(), skill="dsar", event="response.drafted", ref=req_id,
        data={
            "word_count": len(result.split()),
            "requires_human_signoff": True,
            "draft_hash": _hash(result),
        },
    )
    print(
        "\n[civiclaw] Article 14 human-in-the-loop gate: "
        "this draft MUST be reviewed and approved by a human before sending. "
        "Run `civiclaw approve --ref " + req_id + "` to log the sign-off."
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dsar",
        description="Workloft DSAR Agent — AI-assisted Subject Access Request processing for UK Local Authorities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python3 dsar.py intake sample_request.txt
              python3 dsar.py intake "I wish to request all data you hold about me..."
              python3 dsar.py search "James Wilson"
              python3 dsar.py redact sample_document.txt --subject "James Wilson"
              python3 dsar.py redact sample_document.txt --subject "James Wilson" --requester "Sarah Wilson"
              python3 dsar.py respond --request-id REQ001
        """),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # intake
    p_intake = subparsers.add_parser(
        "intake",
        help="Parse a DSAR request and extract structured information",
    )
    p_intake.add_argument(
        "request_text",
        help="The DSAR request text, or a path to a .txt file containing it",
    )
    p_intake.add_argument(
        "--json", dest="json_output", action="store_true",
        help="Output structured JSON instead of markdown",
    )

    # search
    p_search = subparsers.add_parser(
        "search",
        help="Identify which council data sources likely hold the subject's data",
    )
    p_search.add_argument("subject_name", help="Name of the data subject")

    # redact
    p_redact = subparsers.add_parser(
        "redact",
        help="Redact third-party personal data from a document",
    )
    p_redact.add_argument("document", help="Path to the document to redact")
    p_redact.add_argument(
        "--subject", required=True, help="Name of the data subject (their data is preserved)"
    )
    p_redact.add_argument(
        "--requester",
        help="Name of the requester, if different from subject (their data is also preserved)",
    )

    # respond
    p_respond = subparsers.add_parser(
        "respond",
        help="Draft a formal DSAR response letter",
    )
    p_respond.add_argument(
        "--request-id", required=True, help="Request reference ID (e.g., REQ001)"
    )

    args = parser.parse_args()

    commands = {
        "intake": cmd_intake,
        "search": cmd_search,
        "redact": cmd_redact,
        "respond": cmd_respond,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
