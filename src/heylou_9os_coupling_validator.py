from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from typing import Optional


CENT = Decimal("0.01")


def _to_decimal(value: object) -> Decimal:
    dec = Decimal(str(value))
    return dec.quantize(CENT, rounding=ROUND_HALF_UP)


def _iso_timestamp(value: Optional[datetime] = None) -> str:
    return (value or datetime.utcnow()).replace(microsecond=0).isoformat() + "Z"


@dataclass(frozen=True)
class ProfitSnapshot:
    hotel_id: str
    direct_booking_revenue: Decimal
    avoided_ota_commission: Decimal
    subscription_cost_9os: Decimal
    threshold: Decimal
    profit_eur: Decimal
    guarantee_met: bool
    refund_due: bool
    coupling_period_days: int
    phronesis_ticket: Optional[str]
    snapshot_date: str
    audit_hash: str


def calculate_profit(
    direct_booking_revenue: object,
    avoided_ota_commission: object,
    subscription_cost_9os: object,
) -> Decimal:
    revenue = _to_decimal(direct_booking_revenue)
    ota_saved = _to_decimal(avoided_ota_commission)
    cost = _to_decimal(subscription_cost_9os)
    return (revenue + ota_saved - cost).quantize(CENT, rounding=ROUND_HALF_UP)


def default_threshold(subscription_cost_9os: object, multiplier: object = "1.5") -> Decimal:
    cost = _to_decimal(subscription_cost_9os)
    factor = Decimal(str(multiplier))
    return (cost * factor).quantize(CENT, rounding=ROUND_HALF_UP)


def guarantee_met(profit_eur: object, threshold: object) -> bool:
    return _to_decimal(profit_eur) >= _to_decimal(threshold)


def refund_due(
    guarantee_is_met: bool,
    coupling_period_days: int,
    phronesis_ticket: Optional[str] = None,
) -> bool:
    return (not guarantee_is_met) and coupling_period_days >= 90 and bool(phronesis_ticket)


def build_audit_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_coupling(
    hotel_id: str,
    direct_booking_revenue: object,
    avoided_ota_commission: object,
    subscription_cost_9os: object,
    coupling_period_days: int,
    threshold: Optional[object] = None,
    phronesis_ticket: Optional[str] = None,
    snapshot_date: Optional[date] = None,
) -> ProfitSnapshot:
    cost = _to_decimal(subscription_cost_9os)
    profit = calculate_profit(direct_booking_revenue, avoided_ota_commission, cost)
    effective_threshold = (
        default_threshold(cost) if threshold is None else _to_decimal(threshold)
    )
    is_met = guarantee_met(profit, effective_threshold)
    is_refund_due = refund_due(is_met, coupling_period_days, phronesis_ticket)

    snapshot_day = (snapshot_date or date.today()).isoformat()
    audit_payload = {
        "hotel_id": hotel_id,
        "direct_booking_revenue": str(_to_decimal(direct_booking_revenue)),
        "avoided_ota_commission": str(_to_decimal(avoided_ota_commission)),
        "subscription_cost_9os": str(cost),
        "threshold": str(effective_threshold),
        "profit_eur": str(profit),
        "guarantee_met": is_met,
        "refund_due": is_refund_due,
        "coupling_period_days": coupling_period_days,
        "phronesis_ticket": phronesis_ticket,
        "snapshot_date": snapshot_day,
        "generated_at": _iso_timestamp(),
    }
    audit_hash = build_audit_hash(audit_payload)

    return ProfitSnapshot(
        hotel_id=hotel_id,
        direct_booking_revenue=_to_decimal(direct_booking_revenue),
        avoided_ota_commission=_to_decimal(avoided_ota_commission),
        subscription_cost_9os=cost,
        threshold=effective_threshold,
        profit_eur=profit,
        guarantee_met=is_met,
        refund_due=is_refund_due,
        coupling_period_days=coupling_period_days,
        phronesis_ticket=phronesis_ticket,
        snapshot_date=snapshot_day,
        audit_hash=audit_hash,
    )
# [CRUX-MK]
