"""
EIR skill — configuration.

Captures the Reg 12 + Reg 13 exceptions a council's IG team would weigh, plus
sample request data so `respond` has something to work with out of the box.

Note: under EIR, ALL exceptions are subject to a public-interest test — there
are no "absolute" exceptions. Reg 12(2) embeds a presumption in favour of
disclosure that must be weighed against the exception in every case.
"""

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048

# EIR exceptions — Regulation 12 (information about the environment).
# Every one is qualified; every refusal requires a public-interest test.
REG_12_EXCEPTIONS = [
    {"reg": "Reg 12(4)(a)", "name": "Information not held",
     "notes": "Council does not hold the information at the date of the request."},
    {"reg": "Reg 12(4)(b)", "name": "Manifestly unreasonable",
     "notes": "Comparable to s.14 FOIA vexatiousness; high bar — quantify why."},
    {"reg": "Reg 12(4)(c)", "name": "Request formulated too generally",
     "notes": "Council must offer assistance to the requester to refine before applying."},
    {"reg": "Reg 12(4)(d)", "name": "Material in course of completion",
     "notes": "Drafts, unfinished work; the test is whether disclosure would prejudice completion."},
    {"reg": "Reg 12(4)(e)", "name": "Internal communications",
     "notes": "Includes communications with central government if held by the LA in confidence."},
    {"reg": "Reg 12(5)(a)", "name": "International relations, defence, national security or public safety"},
    {"reg": "Reg 12(5)(b)", "name": "Course of justice / fair trial / disciplinary inquiry"},
    {"reg": "Reg 12(5)(c)", "name": "Intellectual property rights"},
    {"reg": "Reg 12(5)(d)", "name": "Confidentiality of public-authority proceedings",
     "notes": "Confidentiality must be provided for in law (e.g. statute, common law of confidence)."},
    {"reg": "Reg 12(5)(e)", "name": "Confidentiality of commercial / industrial information",
     "notes": "Frequent in planning and procurement contexts; needs evidence the confidentiality is provided for in law to protect a legitimate economic interest."},
    {"reg": "Reg 12(5)(f)", "name": "Interests of the person who provided the information",
     "notes": "Voluntary supply by a third party who did not consent and is not under a legal obligation to disclose."},
    {"reg": "Reg 12(5)(g)", "name": "Protection of the environment to which the information relates",
     "notes": "E.g. exact location of a rare species — disclosure could enable harm."},
]

# Reg 13 — personal data; mirrors s.40 FOIA structure.
REG_13_GUIDANCE = (
    "Reg 13 applies where the requested information is the personal data of a "
    "person other than the requester. Disclosure is governed by UK GDPR — the "
    "lawful basis must be established (typically Art. 6(1)(e) public task or "
    "Art. 6(1)(f) legitimate interest, with an Art. 14 GDPR transparency check). "
    "If disclosure would breach UK GDPR principles, the information is exempt "
    "under Reg 13(1)."
)

# 20 working days, with a Reg 7 extension of up to 20 further working days for
# complex/voluminous requests.
STATUTORY_DEADLINE_WORKING_DAYS = 20
REG_7_EXTENSION_WORKING_DAYS = 20

SAMPLE_REQUESTS = {
    "EIR-2026-001": {
        "id": "EIR-2026-001",
        "date_received": "2026-04-08",
        "deadline": "2026-05-08",
        "requester_name": "Camden Air Quality Action Group",
        "request_text": (
            "Under the Environmental Information Regulations 2004 please supply "
            "all air quality monitoring data — including any roadside diffusion "
            "tube readings, automatic monitoring station outputs, and any modelled "
            "annual mean NO2 concentrations — for sites within 250 metres of any "
            "primary or secondary school in the borough during the period 1 April "
            "2024 to 31 March 2026. Please also provide copies of any internal "
            "correspondence between Environmental Health and the Director of "
            "Public Health regarding exceedances of the EU annual mean NO2 "
            "objective (40 µg/m3) at these sites in the same period."
        ),
        "topics": ["air quality", "schools", "NO2 exceedances", "internal communications"],
        "likely_exceptions_considered": ["Reg 12(4)(e)", "Reg 13", "Reg 12(5)(b)"],
    },
}
