"""
FOI skill — configuration.

Captures the common UK FOIA 2000 exemptions that a council's IG team would
consider when processing a request. Exemptions are split into absolute
(don't require a public-interest test) and qualified (do).
"""

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048

# UK FOIA 2000 fee limit for local authorities.
FEE_LIMIT_POUNDS = 450
FEE_LIMIT_HOURS = 18
FEE_STANDARD_RATE_PER_HOUR = 25  # £25/hr per Fees Regulations 2004

ABSOLUTE_EXEMPTIONS = [
    {"section": "s.21", "name": "Information accessible by other means",
     "notes": "If the information is already reasonably accessible (e.g. council website, publication scheme), apply s.21."},
    {"section": "s.23", "name": "Information supplied by security bodies"},
    {"section": "s.32", "name": "Court records"},
    {"section": "s.34", "name": "Parliamentary privilege"},
    {"section": "s.40", "name": "Personal data",
     "notes": "Use when the request is for another person's personal data (UK GDPR applies). Separate from the s.40(1) self-information provision which routes to DSAR."},
    {"section": "s.41", "name": "Information provided in confidence"},
    {"section": "s.44", "name": "Prohibitions on disclosure by other enactments"},
]

QUALIFIED_EXEMPTIONS = [
    {"section": "s.22", "name": "Information intended for future publication"},
    {"section": "s.24", "name": "National security (qualified under FOIA)"},
    {"section": "s.26", "name": "Defence"},
    {"section": "s.27", "name": "International relations"},
    {"section": "s.28", "name": "Relations within the UK"},
    {"section": "s.29", "name": "The economy"},
    {"section": "s.30", "name": "Investigations and proceedings"},
    {"section": "s.31", "name": "Law enforcement"},
    {"section": "s.33", "name": "Audit functions"},
    {"section": "s.35", "name": "Formulation of government policy",
     "notes": "Usually irrelevant for LAs; stays here for completeness."},
    {"section": "s.36", "name": "Prejudice to effective conduct of public affairs",
     "notes": "Requires qualified person (Monitoring Officer, CEO, etc.) opinion. Frequently used by LAs for internal deliberations."},
    {"section": "s.37", "name": "Communications with Her Majesty"},
    {"section": "s.38", "name": "Health and safety"},
    {"section": "s.39", "name": "Environmental information",
     "notes": "If it's environmental information, FOIA s.39 routes the request to the EIR 2004 regime instead."},
    {"section": "s.42", "name": "Legal professional privilege"},
    {"section": "s.43", "name": "Commercial interests",
     "notes": "Common for procurement requests — requires public-interest balance."},
]

# Sample request set so `respond` has something to work with out of the box.
SAMPLE_REQUESTS = {
    "FOI-2026-001": {
        "id": "FOI-2026-001",
        "date_received": "2026-04-02",
        "deadline": "2026-04-30",
        "requester_name": "Press Gazette Investigations Desk",
        "request_text": (
            "Under the Freedom of Information Act 2000 please provide, for the "
            "2024/25 financial year: (a) the total amount paid to external "
            "consultancy firms for advice on digital transformation, broken "
            "down by supplier; (b) copies of any business cases or Cabinet "
            "papers approving spend over £50,000 in this category; and (c) "
            "the job titles of officers who authorised each payment."
        ),
        "topics": ["consultancy spend", "digital transformation", "procurement"],
        "likely_exemptions_considered": ["s.43", "s.36", "s.40"],
        "estimated_hours": 14,
        "estimated_cost": 350,
    },
}
