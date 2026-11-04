"""Synthetic fixtures for the assistante-ventes comparison campaign.

Everything here is invented: part numbers, companies, prices, names. The real
workflow this mirrors belongs to a sales assistant at an aircraft-parts
company whose files never leave her machine; candidates are compared on
lookalike data with the same shape (docs/compare/campaign-assistante.md).

Deterministic by construction: same seed, same bytes, so a fixture change is
a diff, never a surprise. No aprime imports — the comparator consumes the
detector across its public API only, and fixtures need none of it
(tests/test_compare_boundary.py enforces this for the whole package).

    python compare/fixtures_ventes.py        # writes compare/fixtures/
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "fixtures"

SEED = 7

PRODUCTS = [
    ("P-1101", "Roulement de turbine T56", 418.00),
    ("P-1102", "Joint torique haute température", 12.50),
    ("P-1203", "Capteur de pression cabine", 962.00),
    ("P-1204", "Vanne de purge pneumatique", 540.75),
    ("P-1305", "Faisceau électrique APU", 1280.00),
    ("P-1306", "Filtre hydraulique 25 microns", 86.30),
    ("P-1407", "Actuateur de volet", 2310.00),
    ("P-1408", "Hublot de secours classe B", 1745.90),
    ("P-1509", "Kit de visserie titane M6", 64.20),
    ("P-1510", "Amortisseur de train avant", 3150.00),
]

CLIENTS = [
    ("C-201", "Aerolinea del Sur", "ES", "es"),
    ("C-202", "Bergmann Luftfahrt GmbH", "DE", "de"),
    ("C-203", "Capital Air Services", "GB", "en"),
    ("C-204", "Deltaworks Aviation", "US", "en"),
    ("C-205", "Ailes de Provence", "FR", "fr"),
    ("C-206", "Aviazione Lombarda", "IT", "it"),
    ("C-207", "Nordic Rotor Oy", "FI", "en"),
    ("C-208", "Atlas Aéro Maroc", "MA", "fr"),
]

STATUSES = ["payée", "en attente", "en retard", "partiellement expédiée",
            "expédiée", "litige"]


def build_orders(rng: random.Random, n: int = 48) -> list[dict]:
    rows = []
    for i in range(n):
        pid, _, unit = PRODUCTS[rng.randrange(len(PRODUCTS))]
        cid = CLIENTS[rng.randrange(len(CLIENTS))][0]
        qty = rng.choice([1, 2, 2, 3, 4, 5, 8, 10, 12])
        tax = rng.choice([0.0, 5.5, 20.0])
        total = round(qty * unit * (1 + tax / 100), 2)
        day = rng.randrange(1, 28)
        month = rng.choice([7, 8, 9, 10])
        rows.append({
            "order_id": f"CMD-2026-{1000 + i}",
            "order_date": f"2026-{month:02d}-{day:02d}",
            "client_id": cid,
            "product_id": pid,
            "qty": qty,
            "unit_price_eur": f"{unit:.2f}",
            "tax_rate_pct": f"{tax:.1f}",
            "total_eur": f"{total:.2f}",
            "status": STATUSES[rng.randrange(len(STATUSES))],
            "payment_due": f"2026-{month + 1:02d}-{day:02d}",
        })
    return rows


# Inbound client messages: the three real themes (late payment, incomplete
# shipment, discount asks), in the languages her clients actually write.
MESSAGES_IN = [
    {"id": "msg-01", "lang": "en", "theme": "late_payment",
     "text": "Hello, regarding invoice CMD-2026-1004, our accounts team "
             "confirms payment will be executed next Friday. Apologies for "
             "the delay, we had an internal approval backlog."},
    {"id": "msg-02", "lang": "de", "theme": "incomplete_shipment",
     "text": "Guten Tag, die Lieferung zu CMD-2026-1011 ist unvollständig "
             "angekommen. Es fehlen 2 von 5 Stück der Position P-1204. "
             "Bitte senden Sie die fehlende Menge schnellstmöglich nach."},
    {"id": "msg-03", "lang": "es", "theme": "discount_request",
     "text": "Buenos días, somos cliente habitual desde 2023. ¿Sería posible "
             "un descuento del 8% en el pedido CMD-2026-1017 por volumen? "
             "Pensamos repetir pedidos similares cada trimestre."},
    {"id": "msg-04", "lang": "en", "theme": "discount_request",
     "text": "Hi, before confirming CMD-2026-1020 we would like to discuss "
             "pricing: your quote is 6% above your competitor for the same "
             "part. Can you match it or offer free shipping?"},
    {"id": "msg-05", "lang": "it", "theme": "late_payment",
     "text": "Buongiorno, ci scusiamo per il ritardo nel pagamento della "
             "fattura CMD-2026-1008. Il bonifico partirà entro mercoledì. "
             "Potete confermare che la spedizione non sarà bloccata?"},
    {"id": "msg-06", "lang": "de", "theme": "discount_request",
     "text": "Sehr geehrte Damen und Herren, bei einer Abnahme von 12 Stück "
             "P-1306 jährlich: welchen Rahmenvertragspreis können Sie "
             "anbieten?"},
    {"id": "msg-07", "lang": "en", "theme": "incomplete_shipment",
     "text": "Good afternoon, order CMD-2026-1026 arrived today but the "
             "titanium screw kit P-1509 is missing from the box. The packing "
             "list mentions it. Please advise."},
    {"id": "msg-08", "lang": "fr", "theme": "late_payment",
     "text": "Bonjour, nous accusons un léger retard de trésorerie ce "
             "mois-ci. Le règlement de CMD-2026-1002 sera effectué sous 10 "
             "jours. Merci de votre compréhension."},
    {"id": "msg-09", "lang": "en", "theme": "late_payment",
     "text": "Dear team, invoice CMD-2026-1030 slipped through our month-end "
             "run. Payment is scheduled for the 15th. Can you waive the late "
             "fee this once?"},
    {"id": "msg-10", "lang": "de", "theme": "late_payment",
     "text": "Hallo, unsere Buchhaltung hat die Rechnung CMD-2026-1013 "
             "zurückgehalten, weil die Bestellnummer fehlte. Bitte senden Sie "
             "eine korrigierte Rechnung, dann zahlen wir sofort."},
    {"id": "msg-11", "lang": "es", "theme": "late_payment",
     "text": "Estimados, el pago de CMD-2026-1021 se retrasará una semana por "
             "el cierre fiscal. Les rogamos no suspender los envíos en curso."},
    {"id": "msg-12", "lang": "it", "theme": "incomplete_shipment",
     "text": "Salve, nel collo di CMD-2026-1034 mancano i sensori P-1203, 1 "
             "pezzo su 3. La bolla di consegna indica 3. Attendo istruzioni "
             "per il reclamo."},
    {"id": "msg-13", "lang": "en", "theme": "incomplete_shipment",
     "text": "Hi, we received order CMD-2026-1037 with visible transport "
             "damage on the actuator crate. We refused delivery of that item "
             "only. Please arrange a replacement and tell us who files the "
             "carrier claim."},
    {"id": "msg-14", "lang": "es", "theme": "incomplete_shipment",
     "text": "Buenas tardes, faltan 4 unidades de P-1306 en el pedido "
             "CMD-2026-1041. Además, una caja llegó abierta. Solicitamos envío "
             "urgente de lo que falta."},
    {"id": "msg-15", "lang": "de", "theme": "discount_request",
     "text": "Guten Tag, wir planen die Wartung von drei Maschinen im Winter. "
             "Bei Bündelung aller Ersatzteile über Sie: ist ein Projektrabatt "
             "von 10% denkbar?"},
    {"id": "msg-16", "lang": "it", "theme": "discount_request",
     "text": "Buongiorno, il vostro listino per P-1407 è salito del 7% "
             "quest'anno. Siamo clienti dal 2021: potete mantenere il prezzo "
             "2025 almeno fino a marzo?"},
    {"id": "msg-17", "lang": "fr", "theme": "discount_request",
     "text": "Bonjour, pour la commande CMD-2026-1044 nous souhaiterions un "
             "geste commercial : 5% ou le port offert, au choix. Nous avons "
             "doublé nos volumes cette année."},
    {"id": "msg-18", "lang": "en", "theme": "late_payment",
     "text": "Hello, quick heads up: our bank flagged the transfer for "
             "CMD-2026-1046 for additional verification. Funds should clear "
             "within 3 business days. Sorry for the inconvenience."},
    {"id": "msg-19", "lang": "de", "theme": "incomplete_shipment",
     "text": "Sehr geehrtes Team, bei CMD-2026-1048 wurde statt des Kits "
             "P-1509 ein falscher Artikel geliefert. Wir benötigen den "
             "richtigen Artikel bis Freitag, sonst steht die Linie."},
    {"id": "msg-20", "lang": "fr", "theme": "incomplete_shipment",
     "text": "Bonjour, le hublot P-1408 de la commande CMD-2026-1050 est "
             "arrivé fissuré. Photos en pièce jointe. Merci de nous indiquer "
             "la marche à suivre pour le retour."},
    {"id": "msg-21", "lang": "en", "theme": "discount_request",
     "text": "Good morning, we are preparing a tender for a regional "
             "operator. Could you provide your best net prices on P-1101 and "
             "P-1305 for quantities of 20+? Decision expected in two weeks."},
    {"id": "msg-22", "lang": "es", "theme": "discount_request",
     "text": "Hola, ¿aplican descuento por pronto pago? Podemos pagar "
             "CMD-2026-1052 a 5 días en lugar de 30 si ofrecen un 2%."},
    {"id": "msg-23", "lang": "it", "theme": "late_payment",
     "text": "Gentili signori, abbiamo un contenzioso interno sul budget e il "
             "pagamento di CMD-2026-1055 slitterà di 15 giorni. Possiamo "
             "concordare un piano in due rate?"},
    {"id": "msg-24", "lang": "fr", "theme": "late_payment",
     "text": "Bonjour, notre direction financière demande une copie du bon de "
             "livraison signé avant de régler CMD-2026-1058. Pouvez-vous nous "
             "l'envoyer ? Le paiement partira ensuite sous 48 h."},
]

# Outbound situations she writes most: the reminder, and answers to the
# three inbound themes. The model drafts in French, optionally in the
# client's language when it can.
OUTBOUND = [
    {"id": "out-01", "kind": "payment_reminder",
     "brief": "Relance polie: CMD-2026-1015, échéance dépassée de 12 jours, "
              "client C-202, premier rappel."},
    {"id": "out-02", "kind": "payment_reminder",
     "brief": "Relance ferme: CMD-2026-1007, deuxième rappel, proposer un "
              "échéancier si besoin."},
    {"id": "out-03", "kind": "answer_incomplete_shipment",
     "brief": "Répondre à msg-02: confirmer l'envoi des 2 pièces manquantes "
              "sous 48h, numéro de suivi à venir, présenter des excuses."},
    {"id": "out-04", "kind": "answer_discount",
     "brief": "Répondre à msg-03: accorder 5% (pas 8%) si engagement sur 4 "
              "trimestres, sinon 3%."},
    {"id": "out-05", "kind": "answer_discount",
     "brief": "Répondre à msg-04: pas d'alignement sur le concurrent, mais "
              "livraison offerte au-delà de 1500 EUR."},
    {"id": "out-06", "kind": "answer_late_payment",
     "brief": "Répondre à msg-05: confirmer que l'expédition n'est pas "
              "bloquée, demander l'avis de virement."},
    {"id": "out-07", "kind": "payment_reminder",
     "brief": "Relance aimable: CMD-2026-1030, accepter de lever les "
              "pénalités une seule fois, rappeler l'échéance du 15."},
    {"id": "out-08", "kind": "payment_reminder",
     "brief": "Relance: CMD-2026-1046, accuser réception de l'information "
              "bancaire, demander confirmation dès que le virement part."},
    {"id": "out-09", "kind": "payment_reminder",
     "brief": "Dernier rappel avant mise en demeure: CMD-2026-1055, proposer "
              "le plan en deux fois demandé, fixer les deux dates."},
    {"id": "out-10", "kind": "answer_incomplete_shipment",
     "brief": "Répondre à msg-13: accepter le remplacement de l'actuateur, "
              "préciser que nous déposons la réclamation transporteur."},
    {"id": "out-11", "kind": "answer_incomplete_shipment",
     "brief": "Répondre à msg-19: article correct expédié en express "
              "aujourd'hui, étiquette retour jointe pour l'article erroné."},
    {"id": "out-12", "kind": "answer_incomplete_shipment",
     "brief": "Répondre à msg-20: accepter le retour du hublot fissuré, "
              "avoir ou remplacement au choix du client."},
    {"id": "out-13", "kind": "answer_discount",
     "brief": "Répondre à msg-15: 7% sur le projet hiver si commande unique "
              "avant fin novembre, 10% refusé poliment."},
    {"id": "out-14", "kind": "answer_discount",
     "brief": "Répondre à msg-21: tarifs nets à 20+ pièces envoyés sous pli "
              "séparé, validité 30 jours, mentionner le support avant-vente "
              "pour l'appel d'offres."},
    {"id": "out-15", "kind": "answer_discount",
     "brief": "Répondre à msg-22: accepter 2% pour paiement à 5 jours, "
              "préciser que l'escompte figure sur la facture."},
    {"id": "out-16", "kind": "answer_late_payment",
     "brief": "Répondre à msg-24: bon de livraison signé joint, demander le "
              "règlement sous 48 h comme convenu."},
]


def write_fixtures() -> list[Path]:
    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    written = []

    orders = build_orders(rng)
    p = OUT / "orders.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(orders[0].keys()))
        w.writeheader()
        w.writerows(orders)
    written.append(p)

    p = OUT / "products.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["product_id", "designation", "unit_price_eur"])
        for pid, name, price in PRODUCTS:
            w.writerow([pid, name, f"{price:.2f}"])
    written.append(p)

    p = OUT / "clients.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["client_id", "company", "country", "language"])
        for row in CLIENTS:
            w.writerow(row)
    written.append(p)

    p = OUT / "messages.json"
    p.write_text(json.dumps({"inbound": MESSAGES_IN, "outbound": OUTBOUND},
                            ensure_ascii=False, indent=2), encoding="utf-8")
    written.append(p)
    return written


if __name__ == "__main__":
    for path in write_fixtures():
        print(f"wrote {path.relative_to(HERE.parent)}")
