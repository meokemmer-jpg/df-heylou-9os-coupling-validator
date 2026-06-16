from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json
from typing import Optional


_DECIMAL_PLACES = Decimal("0.01")
_TICKET_PREFIX = "PHRONESIS_TICKET-"


def _to_decimal(value: object) -> Decimal:
    return Decimal(str(value)).quantize(_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ProfitSnapshot:
    direct_booking_revenue: Decimal
    avoided_ota_commission: Decimal
    subscription_cost_9os: Decimal
    threshold: Decimal
    coupling_period_days: int
    profit_eur: Decimal
    guarantee_met: bool
    refund_due: bool
    previous_audit_hash: str
    audit_hash: str


def calculate_profit_eur(
    direct_booking_revenue: object,
    avoided_ota_commission: object,
    subscription_cost_9os: object,
) -> Decimal:
    revenue = _to_decimal(direct_booking_revenue)
    ota_savings = _to_decimal(avoided_ota_commission)
    cost = _to_decimal(subscription_cost_9os)
    return (revenue + ota_savings - cost).quantize(_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


def default_threshold(subscription_cost_9os: object) -> Decimal:
    cost = _to_decimal(subscription_cost_9os)
    return (cost * Decimal("1.5")).quantize(_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


def _build_audit_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def evaluate_coupling(
    direct_booking_revenue: object,
    avoided_ota_commission: object,
    subscription_cost_9os: object,
    *,
    threshold: Optional[object] = None,
    coupling_period_days: int = 0,
    previous_audit_hash: str = "GENESIS",
) -> ProfitSnapshot:
    if coupling_period_days < 0:
        raise ValueError("coupling_period_days must be >= 0")

    revenue = _to_decimal(direct_booking_revenue)
    ota_savings = _to_decimal(avoided_ota_commission)
    cost = _to_decimal(subscription_cost_9os)
    applied_threshold = default_threshold(cost) if threshold is None else _to_decimal(threshold)

    profit = calculate_profit_eur(revenue, ota_savings, cost)
    guarantee_met = profit >= applied_threshold
    refund_due = (not guarantee_met) and coupling_period_days >= 90

    hash_payload = {
        "direct_booking_revenue": str(revenue),
        "avoided_ota_commission": str(ota_savings),
        "subscription_cost_9os": str(cost),
        "threshold": str(applied_threshold),
        "coupling_period_days": coupling_period_days,
        "profit_eur": str(profit),
        "guarantee_met": guarantee_met,
        "refund_due": refund_due,
        "previous_audit_hash": previous_audit_hash,
    }
    audit_hash = _build_audit_hash(hash_payload)

    return ProfitSnapshot(
        direct_booking_revenue=revenue,
        avoided_ota_commission=ota_savings,
        subscription_cost_9os=cost,
        threshold=applied_threshold,
        coupling_period_days=coupling_period_days,
        profit_eur=profit,
        guarantee_met=guarantee_met,
        refund_due=refund_due,
        previous_audit_hash=previous_audit_hash,
        audit_hash=audit_hash,
    )


def refund_release_allowed(snapshot: ProfitSnapshot, phronesis_ticket: Optional[str]) -> bool:
    return bool(snapshot.refund_due and phronesis_ticket and phronesis_ticket.startswith(_TICKET_PREFIX))


def snapshot_to_dict(snapshot: ProfitSnapshot) -> dict:
    data = asdict(snapshot)
    for key, value in data.items():
        if isinstance(value, Decimal):
            data[key] = str(value)
    return data
# [CRUX-MK]
