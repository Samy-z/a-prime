"""Knowledge packs: the domain content behind a cell's tools.

A pack is **data, not behaviour**. It holds records, policies, histories,
documents and cases, and the eight tools are deterministic lookups over it. That
matters for three reasons.

**Tool results are ground truth.** Nothing about a tool's answer depends on a
model, so when a retrieval fault is injected we know exactly what the correct
answer was and exactly what the system saw instead.

**Faults can be injected precisely.** Corrupting a pack entry, or making one
lookup return stale data, touches a knowable set of inputs. That is what
per-input activation instrumentation needs.

**The three domains are structurally identical.** Same record shapes, same
policy shapes, same history shapes, differing only in vocabulary and subject
matter. If the detector behaves differently on banking than on logistics, the
difference cannot be that one domain happened to get a richer pack.

Packs are generated deterministically from a seed rather than hand-written, so
the corpus can be made as large as a study needs without anyone typing records.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field

DOMAINS = ("banking", "logistics", "hospitality")


def _seeded(*parts: str) -> random.Random:
    h = hashlib.sha256("|".join(parts).encode()).digest()
    return random.Random(int.from_bytes(h[:8], "big"))


@dataclass(frozen=True)
class Vocab:
    """Everything domain-specific, so the generator itself is domain-blind."""

    entity_kind: str          # what the primary record is called
    entity_prefix: str        # id prefix, e.g. "AC"
    principal_kind: str
    principal_prefix: str
    event_kind: str           # what the searchable history items are
    event_unit: str
    statuses: tuple[str, ...]
    products: tuple[str, ...]
    policy_topics: tuple[str, ...]
    doc_kinds: tuple[str, ...]
    names: tuple[str, ...]


VOCAB: dict[str, Vocab] = {
    "banking": Vocab(
        entity_kind="account", entity_prefix="AC",
        principal_kind="applicant", principal_prefix="AP",
        event_kind="transaction", event_unit="USD",
        statuses=("open", "frozen", "closed", "under review"),
        products=("personal loan", "fixed-rate mortgage", "buy-to-let mortgage",
                  "overdraft extension"),
        policy_topics=("self-employed borrowers", "buy-to-let", "adverse credit",
                       "income verification"),
        doc_kinds=("payslip", "tax return", "bank statement", "identity document"),
        names=("Maria Okonkwo", "Daniel Ferreira", "Aisha Rahman", "Tomas Brenner",
               "Lena Vasquez", "Peter Lindqvist"),
    ),
    "logistics": Vocab(
        entity_kind="shipment", entity_prefix="SH",
        principal_kind="consignee", principal_prefix="CN",
        event_kind="movement", event_unit="pallets",
        statuses=("in transit", "held at customs", "delivered", "awaiting collection"),
        products=("standard freight", "temperature-controlled", "bonded transit",
                  "express air"),
        policy_topics=("phytosanitary certificates", "bonded warehousing",
                       "dangerous goods", "cold chain tolerance"),
        doc_kinds=("bill of lading", "packing list", "certificate of origin",
                   "customs declaration"),
        names=("Northgate Freight", "Westbay Logistics", "Corvid Shipping",
               "Halcyon Transport", "Meridian Cargo", "Selkie Haulage"),
    ),
    "hospitality": Vocab(
        entity_kind="booking", entity_prefix="BK",
        principal_kind="guest", principal_prefix="GU",
        event_kind="stay", event_unit="nights",
        statuses=("confirmed", "on hold", "cancelled", "checked out"),
        products=("standard rate", "flexible rate", "group booking",
                  "corporate agreement"),
        policy_topics=("cancellation windows", "group deposits",
                       "late arrival", "rate parity"),
        doc_kinds=("identity document", "purchase order", "loyalty card",
                   "corporate authorisation"),
        names=("Marisol Vega", "Peter Lindqvist", "Aisha Rahman", "Tomas Brenner",
               "Grace Adeyemi", "Jonas Halvorsen"),
    ),
}


@dataclass
class Pack:
    domain: str
    vocab: Vocab
    entities: dict[str, dict] = field(default_factory=dict)
    principals: dict[str, dict] = field(default_factory=dict)
    policies: dict[str, dict] = field(default_factory=dict)
    events: dict[str, list[dict]] = field(default_factory=dict)
    documents: dict[str, dict] = field(default_factory=dict)
    cases: dict[str, dict] = field(default_factory=dict)

    def entity_ids(self) -> list[str]:
        return sorted(self.entities)

    def principal_ids(self) -> list[str]:
        return sorted(self.principals)

    def document_ids(self) -> list[str]:
        return sorted(self.documents)

    def case_ids(self) -> list[str]:
        return sorted(self.cases)

    def counts(self) -> dict[str, int]:
        return {
            "entities": len(self.entities),
            "principals": len(self.principals),
            "policies": len(self.policies),
            "events": sum(len(v) for v in self.events.values()),
            "documents": len(self.documents),
            "cases": len(self.cases),
        }


def build_pack(domain: str, n_entities: int = 24, seed: int = 0) -> Pack:
    """Generate a pack. Same structure for every domain, different vocabulary."""
    if domain not in VOCAB:
        raise ValueError(f"unknown domain {domain!r}; known: {DOMAINS}")
    v = VOCAB[domain]
    rng = _seeded("pack", domain, str(seed))
    pack = Pack(domain=domain, vocab=v)

    n_principals = max(4, n_entities // 3)
    for i in range(n_principals):
        pid = f"{v.principal_prefix}-{100 + i}"
        pack.principals[pid] = {
            "id": pid,
            "name": v.names[i % len(v.names)],
            "annual_income": rng.choice([28000, 34000, 41000, 54000, 72000, 96000]),
            "existing_debt": rng.choice([0, 3000, 9000, 18000, 27000]),
            "years_on_record": rng.randint(1, 12),
        }

    pids = pack.principal_ids()
    for i in range(n_entities):
        eid = f"{v.entity_prefix}-{4000 + i * 7}"
        owner = pids[i % len(pids)]
        pack.entities[eid] = {
            "id": eid,
            "kind": v.entity_kind,
            f"{v.principal_kind}_id": owner,
            "status": rng.choice(v.statuses),
            "product": rng.choice(v.products),
            "opened": f"{rng.randint(2019, 2026)}-{rng.randint(1, 12):02d}",
            "quantity": rng.choice([3, 9, 14, 22, 41, 180]),
            "unit": v.event_unit,
        }
        pack.events[eid] = [
            {
                "id": f"{eid}-E{j}",
                "kind": v.event_kind,
                "amount": rng.choice([42, 380, 1250, 5400, 21400, 67000]),
                "unit": v.event_unit,
                "date": f"2026-{rng.randint(1, 9):02d}-{rng.randint(1, 28):02d}",
            }
            for j in range(rng.randint(2, 5))
        ]

    for topic in v.policy_topics:
        pack.policies[topic] = {
            "topic": topic,
            "min_years_on_record": rng.randint(1, 3),
            "max_ratio": rng.choice([0.35, 0.40, 0.45, 0.50]),
            "requires_document": rng.choice(v.doc_kinds),
            "text": (
                f"For {topic}, a {v.principal_kind} must have at least "
                f"{{min_years}} years on record and a ratio at or below "
                f"{{max_ratio}}. A valid {{doc}} is required."
            ),
        }

    for i in range(max(6, n_entities // 2)):
        did = f"DOC-{5500 + i * 3}"
        pack.documents[did] = {
            "id": did,
            "kind": rng.choice(v.doc_kinds),
            "valid": rng.random() > 0.3,
            "expires": f"2027-{rng.randint(1, 12):02d}",
        }

    for i in range(max(4, n_entities // 4)):
        cid = f"CS-{200 + i * 11}"
        pack.cases[cid] = {"id": cid, "state": "open", "assigned": None}

    return pack


def all_packs(n_entities: int = 24, seed: int = 0) -> dict[str, Pack]:
    return {d: build_pack(d, n_entities, seed) for d in DOMAINS}
