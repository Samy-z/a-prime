"""Seed content for the probe suite.

Each seed carries a fixed set of typed fields so that every perturbation is
mechanical and auditable — no perturbation is hand-written per seed, which is
what keeps the suite free of the author's unconscious bias about what "should"
be detectable.

Seeds span four subject domains so the probe suite can answer a question the
headline study also asks, at negligible cost: is channel sensitivity a property
of the perturbation, or of the subject matter?

Field contract (every seed must provide all of these):
    subject / subject_alt   a named entity and a same-type replacement
    number  / number_alt    a quantity and a materially different one
    unit    / unit_alt      a unit of measure and a different one
    verdict / verdict_alt   an outcome word and its opposite
    quantifier / quantifier_alt   a universal and an existential
    date    / date_alt      a time reference and a different one
    caveat                  a material condition, as a standalone sentence
    detail1 / detail2       two order-independent facts
    action                  what was done, as a noun phrase
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Seed:
    id: str
    domain: str
    fields: dict[str, str]


_RAW: list[tuple[str, str, dict[str, str]]] = [
    # ---------------------------------------------------------------- banking
    (
        "bank_01",
        "banking",
        {
            "subject": "Maria Okonkwo",
            "subject_alt": "Daniel Ferreira",
            "number": "42,000",
            "number_alt": "67,000",
            "unit": "USD",
            "unit_alt": "EUR",
            "verdict": "approved",
            "verdict_alt": "declined",
            "quantifier": "all",
            "quantifier_alt": "some",
            "date": "March 2026",
            "date_alt": "September 2026",
            "caveat": "Disbursement is conditional on proof of income being filed first.",
            "detail1": "The debt-to-income ratio sits within policy limits.",
            "detail2": "No adverse credit events appear in the last six years.",
            "action": "term loan application",
        },
    ),
    (
        "bank_02",
        "banking",
        {
            "subject": "Northgate Holdings",
            "subject_alt": "Westbay Partners",
            "number": "1,250,000",
            "number_alt": "850,000",
            "unit": "USD",
            "unit_alt": "GBP",
            "verdict": "cleared",
            "verdict_alt": "blocked",
            "quantifier": "all",
            "quantifier_alt": "several",
            "date": "January 2026",
            "date_alt": "November 2025",
            "caveat": "Settlement must complete before the counterparty limit resets.",
            "detail1": "The originating account has a nine-year history.",
            "detail2": "Beneficiary screening returned no sanctions matches.",
            "action": "wire transfer",
        },
    ),
    (
        "bank_03",
        "banking",
        {
            "subject": "Aisha Rahman",
            "subject_alt": "Tomas Brenner",
            "number": "18.5",
            "number_alt": "24.9",
            "unit": "percent",
            "unit_alt": "basis points",
            "verdict": "eligible",
            "verdict_alt": "ineligible",
            "quantifier": "all",
            "quantifier_alt": "most",
            "date": "Q2 2026",
            "date_alt": "Q4 2026",
            "caveat": "The rate is fixed only for the first twelve months.",
            "detail1": "The applicant holds two existing products with the bank.",
            "detail2": "Employment has been continuous for four years.",
            "action": "refinancing request",
        },
    ),
    (
        "bank_04",
        "banking",
        {
            "subject": "Corvid Asset Management",
            "subject_alt": "Halcyon Capital",
            "number": "3",
            "number_alt": "11",
            "unit": "business days",
            "unit_alt": "calendar weeks",
            "verdict": "compliant",
            "verdict_alt": "non-compliant",
            "quantifier": "all",
            "quantifier_alt": "a subset of",
            "date": "February 2026",
            "date_alt": "August 2026",
            "caveat": "This finding excludes positions held through the Luxembourg vehicle.",
            "detail1": "Reporting was submitted through the standard channel.",
            "detail2": "The prior period review raised no open items.",
            "action": "disclosure filing",
        },
    ),
    # -------------------------------------------------------------- logistics
    (
        "logi_01",
        "logistics",
        {
            "subject": "Container MSKU4471820",
            "subject_alt": "Container TGHU9930514",
            "number": "14",
            "number_alt": "31",
            "unit": "pallets",
            "unit_alt": "crates",
            "verdict": "released",
            "verdict_alt": "held",
            "quantifier": "all",
            "quantifier_alt": "some",
            "date": "12 April 2026",
            "date_alt": "26 May 2026",
            "caveat": "Release applies only once the phytosanitary certificate is lodged.",
            "detail1": "The vessel berthed on schedule.",
            "detail2": "Temperature logs stayed inside the required band throughout.",
            "action": "customs clearance",
        },
    ),
    (
        "logi_02",
        "logistics",
        {
            "subject": "Route R-88 Rotterdam-Lyon",
            "subject_alt": "Route R-42 Hamburg-Milan",
            "number": "620",
            "number_alt": "940",
            "unit": "kilometres",
            "unit_alt": "miles",
            "verdict": "viable",
            "verdict_alt": "unviable",
            "quantifier": "all",
            "quantifier_alt": "two of the",
            "date": "June 2026",
            "date_alt": "October 2026",
            "caveat": "The estimate assumes the Alpine tunnel stays open to freight.",
            "detail1": "Driver hours fit within a single shift.",
            "detail2": "Two certified rest stops lie on the corridor.",
            "action": "routing proposal",
        },
    ),
    (
        "logi_03",
        "logistics",
        {
            "subject": "Warehouse Node 7",
            "subject_alt": "Warehouse Node 3",
            "number": "2,400",
            "number_alt": "1,150",
            "unit": "square metres",
            "unit_alt": "square feet",
            "verdict": "sufficient",
            "verdict_alt": "insufficient",
            "quantifier": "all",
            "quantifier_alt": "part of the",
            "date": "week 18",
            "date_alt": "week 33",
            "caveat": "Capacity is quoted before the seasonal overflow allocation.",
            "detail1": "Racking was recertified this year.",
            "detail2": "The site runs two shifts on weekdays.",
            "action": "capacity assessment",
        },
    ),
    (
        "logi_04",
        "logistics",
        {
            "subject": "Shipment BL-20461",
            "subject_alt": "Shipment BL-77329",
            "number": "9",
            "number_alt": "22",
            "unit": "days",
            "unit_alt": "hours",
            "verdict": "on schedule",
            "verdict_alt": "delayed",
            "quantifier": "all",
            "quantifier_alt": "most of the",
            "date": "3 March 2026",
            "date_alt": "19 July 2026",
            "caveat": "Transit time excludes any inspection hold at the destination port.",
            "detail1": "The booking was confirmed against a firm allocation.",
            "detail2": "Documentation cleared pre-arrival review.",
            "action": "delivery estimate",
        },
    ),
    # ------------------------------------------------------------ hospitality
    (
        "hosp_01",
        "hospitality",
        {
            "subject": "The Laurel Court",
            "subject_alt": "The Ashgrove Inn",
            "number": "4",
            "number_alt": "9",
            "unit": "nights",
            "unit_alt": "weeks",
            "verdict": "confirmed",
            "verdict_alt": "cancelled",
            "quantifier": "all",
            "quantifier_alt": "two of the",
            "date": "15 August 2026",
            "date_alt": "2 December 2026",
            "caveat": "The rate holds only if the stay is prepaid in full.",
            "detail1": "The room type matches the original request.",
            "detail2": "Late checkout was noted on the reservation.",
            "action": "booking",
        },
    ),
    (
        "hosp_02",
        "hospitality",
        {
            "subject": "Guest record 88-4102",
            "subject_alt": "Guest record 88-6337",
            "number": "175",
            "number_alt": "320",
            "unit": "EUR",
            "unit_alt": "CHF",
            "verdict": "refundable",
            "verdict_alt": "non-refundable",
            "quantifier": "all",
            "quantifier_alt": "certain",
            "date": "7 September 2026",
            "date_alt": "21 January 2027",
            "caveat": "Cancellation inside 48 hours forfeits the deposit.",
            "detail1": "The booking was made through the direct channel.",
            "detail2": "A loyalty tier discount has already been applied.",
            "action": "rate quotation",
        },
    ),
    (
        "hosp_03",
        "hospitality",
        {
            "subject": "Banquet Hall B",
            "subject_alt": "Banquet Hall D",
            "number": "180",
            "number_alt": "95",
            "unit": "seated guests",
            "unit_alt": "standing guests",
            "verdict": "available",
            "verdict_alt": "unavailable",
            "quantifier": "all",
            "quantifier_alt": "half of the",
            "date": "30 October 2026",
            "date_alt": "14 February 2027",
            "caveat": "Availability assumes the adjoining terrace is not required.",
            "detail1": "The room has step-free access from the lobby.",
            "detail2": "In-house catering covers the full menu range.",
            "action": "venue hold",
        },
    ),
    (
        "hosp_04",
        "hospitality",
        {
            "subject": "Marisol Vega",
            "subject_alt": "Peter Lindqvist",
            "number": "2",
            "number_alt": "6",
            "unit": "adjoining rooms",
            "unit_alt": "suites",
            "verdict": "granted",
            "verdict_alt": "refused",
            "quantifier": "all",
            "quantifier_alt": "one of the",
            "date": "11 June 2026",
            "date_alt": "28 November 2026",
            "caveat": "The upgrade lapses if arrival is after midnight.",
            "detail1": "The party includes two children under twelve.",
            "detail2": "A previous stay was recorded last spring.",
            "action": "upgrade request",
        },
    ),
    # -------------------------------------------------------------- technical
    (
        "tech_01",
        "technical",
        {
            "subject": "service auth-gateway",
            "subject_alt": "service billing-sync",
            "number": "350",
            "number_alt": "1,800",
            "unit": "milliseconds",
            "unit_alt": "seconds",
            "verdict": "healthy",
            "verdict_alt": "degraded",
            "quantifier": "all",
            "quantifier_alt": "three of the",
            "date": "14 May 2026",
            "date_alt": "1 October 2026",
            "caveat": "The measurement excludes traffic from the canary pool.",
            "detail1": "Error rates stayed below the alerting threshold.",
            "detail2": "The deployment completed without rollback.",
            "action": "latency review",
        },
    ),
    (
        "tech_02",
        "technical",
        {
            "subject": "index shard 12",
            "subject_alt": "index shard 5",
            "number": "97.4",
            "number_alt": "62.8",
            "unit": "percent",
            "unit_alt": "per mille",
            "verdict": "consistent",
            "verdict_alt": "inconsistent",
            "quantifier": "all",
            "quantifier_alt": "a handful of",
            "date": "9 February 2026",
            "date_alt": "23 August 2026",
            "caveat": "Replicas in the secondary region were not included in this check.",
            "detail1": "The checksum job ran to completion.",
            "detail2": "No write conflicts were logged during the window.",
            "action": "integrity check",
        },
    ),
    (
        "tech_03",
        "technical",
        {
            "subject": "migration step 4",
            "subject_alt": "migration step 9",
            "number": "16",
            "number_alt": "48",
            "unit": "minutes",
            "unit_alt": "hours",
            "verdict": "reversible",
            "verdict_alt": "irreversible",
            "quantifier": "all",
            "quantifier_alt": "most",
            "date": "5 July 2026",
            "date_alt": "17 December 2026",
            "caveat": "Reversal requires the pre-migration snapshot to still exist.",
            "detail1": "The step runs inside a single transaction.",
            "detail2": "Downstream consumers are paused for its duration.",
            "action": "rollback assessment",
        },
    ),
    (
        "tech_04",
        "technical",
        {
            "subject": "certificate CN=api.internal",
            "subject_alt": "certificate CN=edge.internal",
            "number": "21",
            "number_alt": "90",
            "unit": "days",
            "unit_alt": "months",
            "verdict": "valid",
            "verdict_alt": "expired",
            "quantifier": "all",
            "quantifier_alt": "two of the",
            "date": "28 April 2026",
            "date_alt": "6 September 2026",
            "caveat": "Renewal depends on the registrar contact being reachable.",
            "detail1": "The chain resolves to a trusted root.",
            "detail2": "Automated rotation is configured for this host.",
            "action": "expiry audit",
        },
    ),
]

# Syntactic negation of detail1, written out per seed rather than derived.
# A rule-based negator would introduce its own grammatical failures, and those
# failures would be indistinguishable from the channel blindness the suite is
# trying to measure.
_DETAIL1_NEG: dict[str, str] = {
    "bank_01": "The debt-to-income ratio does not sit within policy limits.",
    "bank_02": "The originating account does not have a nine-year history.",
    "bank_03": "The applicant does not hold any existing products with the bank.",
    "bank_04": "Reporting was not submitted through the standard channel.",
    "logi_01": "The vessel did not berth on schedule.",
    "logi_02": "Driver hours do not fit within a single shift.",
    "logi_03": "Racking was not recertified this year.",
    "logi_04": "The booking was not confirmed against a firm allocation.",
    "hosp_01": "The room type does not match the original request.",
    "hosp_02": "The booking was not made through the direct channel.",
    "hosp_03": "The room does not have step-free access from the lobby.",
    "hosp_04": "The party does not include any children under twelve.",
    "tech_01": "Error rates did not stay below the alerting threshold.",
    "tech_02": "The checksum job did not run to completion.",
    "tech_03": "The step does not run inside a single transaction.",
    "tech_04": "The chain does not resolve to a trusted root.",
}

SEEDS: list[Seed] = [
    Seed(id=i, domain=d, fields={**f, "detail1_alt": _DETAIL1_NEG[i]})
    for i, d, f in _RAW
]

REQUIRED_FIELDS = (
    "subject",
    "subject_alt",
    "number",
    "number_alt",
    "unit",
    "unit_alt",
    "verdict",
    "verdict_alt",
    "quantifier",
    "quantifier_alt",
    "date",
    "date_alt",
    "caveat",
    "detail1",
    "detail1_alt",
    "detail2",
    "action",
)

DOMAINS = sorted({s.domain for s in SEEDS})
