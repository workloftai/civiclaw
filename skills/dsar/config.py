"""
DSAR Agent — Configuration and mock data sources.

Defines the simulated LA data landscape that the agent searches
when locating records for a data subject.
"""

# Mock data sources a typical Local Authority would hold
DATA_SOURCES = [
    {
        "id": "SIS",
        "name": "Schools Information System",
        "description": "Pupil enrolment, attendance, exclusions, SEN status, free school meals eligibility",
        "data_types": ["enrolment records", "attendance logs", "exclusion records", "SEN flags", "FSM eligibility"],
        "retention_years": 25,
        "controller": "Education Services",
    },
    {
        "id": "SCSS",
        "name": "Social Care Case System",
        "description": "Children's social care referrals, assessments, child protection plans, looked-after children records",
        "data_types": ["referral records", "assessment reports", "CP plans", "LAC records", "foster placement data"],
        "retention_years": 75,
        "controller": "Children's Social Care",
    },
    {
        "id": "EHCP",
        "name": "EHC Plan Database",
        "description": "Education, Health and Care plans, annual reviews, professional assessments",
        "data_types": ["EHC plans", "annual review documents", "EP reports", "SALT reports", "OT reports"],
        "retention_years": 25,
        "controller": "SEN & Inclusion",
    },
    {
        "id": "TRANS",
        "name": "Transport Management System",
        "description": "Home-to-school transport applications, route assignments, medical/mobility needs",
        "data_types": ["transport applications", "route assignments", "medical needs", "pickup/dropoff addresses"],
        "retention_years": 6,
        "controller": "School Transport",
    },
    {
        "id": "ADMIS",
        "name": "Admissions Database",
        "description": "School place applications, preference rankings, appeals, in-year transfers",
        "data_types": ["application forms", "preference lists", "appeal records", "offer letters"],
        "retention_years": 7,
        "controller": "Admissions Team",
    },
    {
        "id": "YOUTH",
        "name": "Youth Offending Service",
        "description": "Youth justice records, intervention plans, court reports, reparation orders",
        "data_types": ["offending records", "intervention plans", "court reports", "risk assessments"],
        "retention_years": 25,
        "controller": "Youth Justice Service",
    },
    {
        "id": "EWO",
        "name": "Education Welfare Records",
        "description": "Non-attendance referrals, penalty notices, school attendance orders, CME records",
        "data_types": ["welfare referrals", "penalty notices", "attendance orders", "CME tracking"],
        "retention_years": 10,
        "controller": "Education Welfare",
    },
    {
        "id": "HOUSING",
        "name": "Housing Services Database",
        "description": "Housing applications, tenancy records, homelessness assessments, temporary accommodation",
        "data_types": ["housing applications", "tenancy agreements", "homelessness assessments", "TA placements"],
        "retention_years": 15,
        "controller": "Housing Services",
    },
    {
        "id": "REVS",
        "name": "Revenues & Benefits System",
        "description": "Council tax accounts, housing benefit claims, council tax support, discretionary payments",
        "data_types": ["council tax records", "benefit claims", "payment history", "correspondence"],
        "retention_years": 7,
        "controller": "Revenues & Benefits",
    },
    {
        "id": "HR",
        "name": "HR & Payroll System",
        "description": "Employee records, DBS checks, training logs, sickness absence, pay records",
        "data_types": ["personnel files", "DBS records", "training records", "absence data", "payroll data"],
        "retention_years": 7,
        "controller": "Human Resources",
    },
]

# Simulated request log (for the respond subcommand)
SAMPLE_REQUESTS = {
    "REQ001": {
        "id": "REQ001",
        "requester_name": "Sarah Wilson",
        "requester_relationship": "Parent",
        "data_subject": "James Wilson",
        "dob": "15/03/2012",
        "date_received": "2026-04-01",
        "deadline": "2026-04-30",
        "scope": "All personal data held by the Council relating to James Wilson",
        "identity_verified": True,
        "authority_verified": True,
        "sources_searched": ["SIS", "EHCP", "ADMIS", "TRANS", "EWO"],
        "documents_found": 14,
        "documents_redacted": 14,
        "exemptions_applied": ["s.15(4) — third-party data redacted"],
        "status": "ready_to_respond",
    },
    "REQ002": {
        "id": "REQ002",
        "requester_name": "Michael Brown",
        "requester_relationship": "Self",
        "data_subject": "Michael Brown",
        "dob": "22/07/1985",
        "date_received": "2026-04-10",
        "deadline": "2026-05-09",
        "scope": "Employment records, DBS checks, and training logs",
        "identity_verified": True,
        "authority_verified": True,
        "sources_searched": ["HR"],
        "documents_found": 8,
        "documents_redacted": 8,
        "exemptions_applied": [],
        "status": "ready_to_respond",
    },
}

# Model configuration
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048
