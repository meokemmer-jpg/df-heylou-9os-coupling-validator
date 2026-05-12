"""Tests fuer DF-HeyLou-9OS-Coupling-Validator [CRUX-MK]. >=20 Tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.coupling_validator import (
    CouplingValidator,
    CouplingHealthStatus,
)
from src.profit_calculator import ProfitCalculator
from src.guarantee_engine import GuaranteeEngine
from src.audit_logger import AuditLogger
from src.validator_orchestrator import ValidatorOrchestrator


# ============== Coupling-Validator Tests ==============

def test_register_coupling():
    """Test 1: Register Coupling-State."""
    v = CouplingValidator()
    s = v.register_coupling("H1", "2026-04-01")
    assert s.hotel_id == "H1"
    assert s.heylou_active is True
    assert s.nine_os_active is True
    assert s.status == CouplingHealthStatus.HEALTHY


def test_update_health_to_degraded():
    """Test 2: Update zu degraded-9os."""
    v = CouplingValidator()
    v.register_coupling("H1", "2026-04-01")
    s = v.update_health("H1", heylou_active=True, nine_os_active=False)
    assert s.status == CouplingHealthStatus.DEGRADED_9OS
    assert s.consecutive_unhealthy_checks == 1


def test_update_health_both_degraded():
    """Test 3: Both DFs degraded → not_coupled."""
    v = CouplingValidator()
    v.register_coupling("H1", "2026-04-01")
    s = v.update_health("H1", heylou_active=False, nine_os_active=False)
    assert s.status == CouplingHealthStatus.NOT_COUPLED


def test_update_health_unknown_hotel_raises():
    """Test 4: Update unbekanntes Hotel raises."""
    v = CouplingValidator()
    with pytest.raises(KeyError):
        v.update_health("UNKNOWN", True, True)


def test_health_recovery_resets_counter():
    """Test 5: Recovery setzt consecutive_unhealthy auf 0."""
    v = CouplingValidator()
    v.register_coupling("H1", "2026-04-01")
    v.update_health("H1", True, False)
    v.update_health("H1", False, False)
    s = v.update_health("H1", True, True)
    assert s.consecutive_unhealthy_checks == 0


# ============== Profit-Calculator Tests ==============

def test_profit_calculation_positive():
    """Test 6: Profit korrekt berechnet."""
    c = ProfitCalculator()
    snap = c.compute_snapshot(
        hotel_id="H1",
        period_start_iso="2026-04-01",
        period_end_iso="2026-06-30",
        direct_revenue_eur=10000.0,
        avoided_ota_commission_eur=1800.0,
        nine_os_cost_eur=600.0,
    )
    # Profit = 10000 + 1800 - 600 = 11200
    assert snap.profit_eur == 11200.0


def test_profit_negative_input_raises():
    """Test 7: Negative inputs raise."""
    c = ProfitCalculator()
    with pytest.raises(ValueError):
        c.compute_snapshot("H1", "a", "b", -100.0, 0.0, 0.0)


def test_profit_margin_calculation():
    """Test 8: Margin korrekt."""
    c = ProfitCalculator()
    snap = c.compute_snapshot("H1", "a", "b", 1000.0, 0.0, 100.0)
    # Profit = 900, denom = 1000, margin = 90%
    assert snap.profit_margin_pct == 90.0


def test_profit_zero_revenue_margin_zero():
    """Test 9: Zero-Revenue → margin = 0."""
    c = ProfitCalculator()
    snap = c.compute_snapshot("H1", "a", "b", 0.0, 0.0, 100.0)
    assert snap.profit_margin_pct == 0.0


# ============== Guarantee-Engine Tests ==============

def test_guarantee_met_when_profit_above_threshold():
    """Test 10: Profit >= threshold → guarantee_met=True."""
    e = GuaranteeEngine()
    check = e.check_guarantee(
        hotel_id="H1", period_start_iso="a", period_end_iso="b",
        profit_eur=1200.0, nine_os_cost_eur=600.0, coupling_days=100,
    )
    # threshold = 600 * 1.5 = 900; profit 1200 >= 900 → MET
    assert check.guarantee_met is True
    assert check.refund_eligible is False


def test_guarantee_not_met_refund_eligible():
    """Test 11: Profit < threshold + 90+ Tage → refund_eligible."""
    e = GuaranteeEngine()
    check = e.check_guarantee(
        hotel_id="H1", period_start_iso="a", period_end_iso="b",
        profit_eur=500.0, nine_os_cost_eur=600.0, coupling_days=100,
    )
    # threshold = 900; profit 500 < 900 + 100 Tage >= 90 → eligible
    assert check.guarantee_met is False
    assert check.refund_eligible is True
    assert check.refund_eur > 0


def test_guarantee_not_eligible_before_90_days():
    """Test 12: < 90 Tage → NICHT refund_eligible."""
    e = GuaranteeEngine()
    check = e.check_guarantee(
        hotel_id="H1", period_start_iso="a", period_end_iso="b",
        profit_eur=100.0, nine_os_cost_eur=600.0, coupling_days=60,
    )
    assert check.refund_eligible is False
    assert check.refund_eur == 0.0


def test_guarantee_refund_capped_at_9os_cost():
    """Test 13: Refund max = 9OS-Cost (kein Hotelier-Profit-from-Refund)."""
    e = GuaranteeEngine()
    check = e.check_guarantee(
        hotel_id="H1", period_start_iso="a", period_end_iso="b",
        profit_eur=-5000.0, nine_os_cost_eur=600.0, coupling_days=100,
    )
    # shortfall = 900 - (-5000) = 5900, aber capped auf 600
    assert check.refund_eur == 600.0


def test_guarantee_custom_multiplier():
    """Test 14: Custom threshold_multiplier."""
    e = GuaranteeEngine()
    check = e.check_guarantee(
        hotel_id="H1", period_start_iso="a", period_end_iso="b",
        profit_eur=2000.0, nine_os_cost_eur=600.0, coupling_days=100,
        threshold_multiplier=2.0,  # Strenger
    )
    # threshold = 600 * 2.0 = 1200; profit 2000 >= 1200 → MET
    assert check.guarantee_met is True


def test_guarantee_invalid_multiplier_raises():
    """Test 15: Negative multiplier raises."""
    e = GuaranteeEngine()
    with pytest.raises(ValueError):
        e.check_guarantee(
            "H1", "a", "b", 100.0, 100.0, 100, threshold_multiplier=-1.0
        )


def test_guarantee_negative_coupling_days_raises():
    """Test 16: Negative coupling_days raises."""
    e = GuaranteeEngine()
    with pytest.raises(ValueError):
        e.check_guarantee("H1", "a", "b", 100.0, 100.0, -1)


def test_trigger_refund_not_eligible():
    """Test 17: trigger_refund auf nicht-eligible-check returns triggered=False."""
    e = GuaranteeEngine()
    check = e.check_guarantee("H1", "a", "b", 1500.0, 600.0, 100)  # met
    r = e.trigger_refund(check)
    assert r["triggered"] is False
    assert r["reason"] == "not_eligible"


def test_trigger_refund_without_phronesis_blocked():
    """Test 18: K_0-CRITICAL: Refund-Trigger ohne PHRONESIS_TICKET blocked."""
    e = GuaranteeEngine()
    check = e.check_guarantee("H1", "a", "b", 100.0, 600.0, 100)  # not met, eligible
    with patch.dict(os.environ, {}, clear=False):
        if "PHRONESIS_TICKET" in os.environ:
            del os.environ["PHRONESIS_TICKET"]
        r = e.trigger_refund(check)
        assert r["triggered"] is False
        assert r["reason"] == "phronesis_ticket_required"


def test_trigger_refund_with_phronesis_succeeds():
    """Test 19: Refund mit PHRONESIS_TICKET triggered=True."""
    e = GuaranteeEngine()
    check = e.check_guarantee("H1", "a", "b", 100.0, 600.0, 100)
    with patch.dict(os.environ, {"PHRONESIS_TICKET": "PT-2026-05-11-001"}, clear=False):
        r = e.trigger_refund(check)
        assert r["triggered"] is True
        assert r["refund_eur"] > 0
        assert r["phronesis_ticket"] == "PT-2026-05-11-001"


# ============== Audit + Orchestrator Tests ==============

def test_audit_chain_coupling(tmp_path):
    """Test 20: Audit-Chain valid."""
    a = AuditLogger(audit_path=tmp_path / "a.jsonl", secret="s")
    a.append({"e": "1"})
    a.append({"e": "2"})
    assert a.verify_chain()["valid"] is True


def test_orchestrator_end_to_end_guarantee_met():
    """Test 21: End-to-End Run mit guarantee_met=True."""
    orch = ValidatorOrchestrator(sandbox_mode=True)
    r = orch.run_check_for_hotel(
        hotel_id="H1",
        period_start_iso="2026-04-01",
        period_end_iso="2026-06-30",
        direct_revenue_eur=15000.0,
        avoided_ota_commission_eur=2700.0,
        nine_os_cost_eur=600.0,
        coupling_days=91,
    )
    assert r.guarantee_met is True
    assert r.refund_eligible is False
    assert r.profit_eur > 0
    assert r.audit_hash != ""


def test_orchestrator_end_to_end_refund_eligible():
    """Test 22: End-to-End Run mit refund_eligible=True."""
    orch = ValidatorOrchestrator(sandbox_mode=True)
    r = orch.run_check_for_hotel(
        hotel_id="H1",
        period_start_iso="2026-04-01",
        period_end_iso="2026-06-30",
        direct_revenue_eur=100.0,  # Sehr niedrig
        avoided_ota_commission_eur=18.0,
        nine_os_cost_eur=600.0,
        coupling_days=120,
    )
    assert r.guarantee_met is False
    assert r.refund_eligible is True
