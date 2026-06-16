import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# [CRUX-MK]
from decimal import Decimal

from heylou_9os_coupling_validator import (
    build_audit_hash,
    calculate_profit,
    default_threshold,
    validate_coupling,
)


def test_profit_guarantee_met_without_refund():
    snapshot = validate_coupling(
        hotel_id="H-100",
        direct_booking_revenue="2000.00",
        avoided_ota_commission="400.00",
        subscription_cost_9os="1000.00",
        coupling_period_days=45,
    )

    assert snapshot.profit_eur == Decimal("1400.00")
    assert snapshot.threshold == Decimal("1500.00")
    assert snapshot.guarantee_met is False
    assert snapshot.refund_due is False


def test_refund_due_after_90_days_requires_phronesis_ticket():
    snapshot = validate_coupling(
        hotel_id="H-200",
        direct_booking_revenue="300.00",
        avoided_ota_commission="100.00",
        subscription_cost_9os="1000.00",
        coupling_period_days=90,
        phronesis_ticket="PHR-777",
    )

    assert snapshot.profit_eur == Decimal("-600.00")
    assert snapshot.guarantee_met is False
    assert snapshot.refund_due is True
    assert len(snapshot.audit_hash) == 64


def test_deterministic_audit_hash_and_threshold():
    threshold = default_threshold("800.00")
    assert threshold == Decimal("1200.00")

    profit = calculate_profit("900.00", "400.00", "800.00")
    assert profit == Decimal("500.00")

    payload = {"hotel_id": "H-300", "profit_eur": "500.00"}
    assert build_audit_hash(payload) == build_audit_hash(dict(payload))
