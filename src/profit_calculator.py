"""Profit-Calculator [CRUX-MK].

Berechnet Profit aus Direct-Revenue + Anti-OTA-Savings - 9OS-Cost.

DETERMINISTIC. Kein LLM. K_0-relevant.

[CRUX-MK]
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class ProfitSnapshot:
    """Profit-Snapshot fuer Hotel + Period."""
    hotel_id: str
    period_start_iso: str
    period_end_iso: str
    direct_booking_revenue_eur: float
    avoided_ota_commission_eur: float
    nine_os_subscription_cost_eur: float
    profit_eur: float
    profit_margin_pct: float
    snapshot_ts: float


class ProfitCalculator:
    """Profit-Berechnung fuer coupled Hotels."""

    def compute_snapshot(
        self,
        hotel_id: str,
        period_start_iso: str,
        period_end_iso: str,
        direct_revenue_eur: float,
        avoided_ota_commission_eur: float,
        nine_os_cost_eur: float,
    ) -> ProfitSnapshot:
        """Deterministische Profit-Berechnung."""
        if direct_revenue_eur < 0 or avoided_ota_commission_eur < 0 or nine_os_cost_eur < 0:
            raise ValueError("Negative inputs not allowed")

        # Profit = Revenue + Savings - Cost
        profit = direct_revenue_eur + avoided_ota_commission_eur - nine_os_cost_eur

        # Margin = profit / total-revenue
        denom = direct_revenue_eur + avoided_ota_commission_eur
        margin = (profit / denom * 100) if denom > 0 else 0.0

        return ProfitSnapshot(
            hotel_id=hotel_id,
            period_start_iso=period_start_iso,
            period_end_iso=period_end_iso,
            direct_booking_revenue_eur=round(direct_revenue_eur, 2),
            avoided_ota_commission_eur=round(avoided_ota_commission_eur, 2),
            nine_os_subscription_cost_eur=round(nine_os_cost_eur, 2),
            profit_eur=round(profit, 2),
            profit_margin_pct=round(margin, 2),
            snapshot_ts=time.time(),
        )
