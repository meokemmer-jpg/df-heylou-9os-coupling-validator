"""Validator-Orchestrator [CRUX-MK]."""

from __future__ import annotations

import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidatorOrchestratorResult:
    hotel_id: str
    coupling_status: str
    profit_eur: float
    guarantee_met: bool
    refund_eligible: bool
    audit_hash: str
    sandbox_mode: bool


class ValidatorOrchestrator:
    def __init__(self, sandbox_mode: Optional[bool] = None):
        from . import coupling_validator, profit_calculator, guarantee_engine, audit_logger
        if sandbox_mode is None:
            sandbox_mode = (
                os.environ.get("DF_HEYLOU_9OS_COUPLING_REAL_ENABLED", "false").lower() != "true"
            )
        self.sandbox_mode = sandbox_mode
        self.coupling = coupling_validator.CouplingValidator()
        self.profit = profit_calculator.ProfitCalculator()
        self.guarantee = guarantee_engine.GuaranteeEngine()
        self.audit = audit_logger.AuditLogger()

    def run_check_for_hotel(
        self,
        hotel_id: str,
        period_start_iso: str,
        period_end_iso: str,
        direct_revenue_eur: float,
        avoided_ota_commission_eur: float,
        nine_os_cost_eur: float,
        coupling_days: int,
    ) -> ValidatorOrchestratorResult:
        """End-to-End Validation per Hotel."""
        # Coupling state-check
        state = self.coupling.get_state(hotel_id)
        if state is None:
            state = self.coupling.register_coupling(
                hotel_id=hotel_id,
                coupling_start_iso=period_start_iso,
            )

        # Profit-Snapshot
        snap = self.profit.compute_snapshot(
            hotel_id=hotel_id,
            period_start_iso=period_start_iso,
            period_end_iso=period_end_iso,
            direct_revenue_eur=direct_revenue_eur,
            avoided_ota_commission_eur=avoided_ota_commission_eur,
            nine_os_cost_eur=nine_os_cost_eur,
        )

        # Guarantee-Check
        check = self.guarantee.check_guarantee(
            hotel_id=hotel_id,
            period_start_iso=period_start_iso,
            period_end_iso=period_end_iso,
            profit_eur=snap.profit_eur,
            nine_os_cost_eur=nine_os_cost_eur,
            coupling_days=coupling_days,
        )

        # Audit
        audit_hash = self.audit.append({
            "type": "coupling_guarantee_check",
            "hotel_id": hotel_id,
            "coupling_status": state.status.value,
            "profit_eur": snap.profit_eur,
            "guarantee_met": check.guarantee_met,
            "refund_eligible": check.refund_eligible,
            "refund_eur": check.refund_eur,
            "sandbox_mode": self.sandbox_mode,
        })

        return ValidatorOrchestratorResult(
            hotel_id=hotel_id,
            coupling_status=state.status.value,
            profit_eur=snap.profit_eur,
            guarantee_met=check.guarantee_met,
            refund_eligible=check.refund_eligible,
            audit_hash=audit_hash,
            sandbox_mode=self.sandbox_mode,
        )


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO)
    if Path("/tmp/df-heylou-9os-coupling.stop").exists():
        return 0
    orch = ValidatorOrchestrator()
    r = orch.run_check_for_hotel(
        hotel_id="HILDESHEIM-PILOT-01",
        period_start_iso="2026-04-01",
        period_end_iso="2026-06-30",
        direct_revenue_eur=15000.0,
        avoided_ota_commission_eur=2700.0,
        nine_os_cost_eur=600.0,
        coupling_days=91,
    )
    logger.info(f"Coupling-Validation: {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
