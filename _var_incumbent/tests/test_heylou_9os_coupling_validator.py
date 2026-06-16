import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# [CRUX-MK]
from decimal import Decimal

from heylou_9os_coupling_validator import (
    calculate_profit_eur,
    default_threshold,
    evaluate_coupling,
    refund_release_allowed,
    snapshot_to_dict,
)


def test_profit_formula_threshold_refund_and_audit_chain():
    assert calculate_profit_eur("1000.00", "250.00", "500.00") == Decimal("750.00")
    assert default_threshold("500.00") == Decimal("750.00")

    success = evaluate_coupling(
        "1000.00",
        "250.00",
        "500.00",
        coupling_period_days=30,
        previous_audit_hash="GENESIS",
    )
    assert success.profit_eur == Decimal("750.00")
    assert success.threshold == Decimal("750.00")
    assert success.guarantee_met is True
    assert success.refund_due is False
    assert refund_release_allowed(success, "PHRONESIS_TICKET-123") is False

    failed = evaluate_coupling(
        "200.00",
        "100.00",
        "500.00",
        coupling_period_days=120,
        previous_audit_hash=success.audit_hash,
    )
    assert failed.profit_eur == Decimal("-200.00")
    assert failed.guarantee_met is False
    assert failed.refund_due is True
    assert failed.previous_audit_hash == success.audit_hash
    assert failed.audit_hash != success.audit_hash

    assert refund_release_allowed(failed, None) is False
    assert refund_release_allowed(failed, "BAD-123") is False
    assert refund_release_allowed(failed, "PHRONESIS_TICKET-MARTIN-OK") is True

    exported = snapshot_to_dict(failed)
    assert exported["profit_eur"] == "-200.00"
    assert exported["refund_due"] is True

