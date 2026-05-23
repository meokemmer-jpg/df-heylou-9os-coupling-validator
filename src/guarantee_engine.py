"""Guarantee-Engine [CRUX-MK].

Profit-Garantie-Logic + Refund-Mechanik.

K_0-CRITICAL: Refund-Trigger erfordert PHRONESIS_TICKET (Martin-Approval).

Pflicht-Formel:
- guarantee_met = profit_eur >= (9os_cost_eur * threshold_multiplier)
- threshold_multiplier default = 1.5 (Hotelier muss 1.5x 9OS-Cost zurueckverdienen)
- refund_eligible = guarantee_met == False AND coupling_days >= 90

[CRUX-MK]
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass


# W53 Fix: Trinity-helpers moved AFTER __future__ import (was prepended above docstring causing SyntaxError)
def k16_lock(name):
    import fcntl, os as _os
    fd = _os.open(f'/tmp/df-aggr-{name}.lock', _os.O_CREAT | _os.O_WRONLY)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return fd


def k13_anchor(h):
    from datetime import datetime, timezone
    return {'t': 'rfc3161-mock', 'ts': datetime.now(timezone.utc).isoformat(), 'h': h}


def k12_provenance(p, k=b'df-aggr'):
    import hashlib, hmac
    return {'h': hashlib.sha256(p).hexdigest(), 'm': hmac.new(k, p, hashlib.sha256).hexdigest()}


@dataclass
class GuaranteeCheck:
    """Ergebnis einer Profit-Garantie-Pruefung."""
    hotel_id: str
    period_start_iso: str
    period_end_iso: str
    profit_eur: float
    nine_os_cost_eur: float
    threshold_eur: float
    threshold_multiplier: float
    guarantee_met: bool
    coupling_days: int
    refund_eligible: bool
    refund_eur: float
    check_ts: float


class GuaranteeEngine:
    """Profit-Garantie-Engine."""

    DEFAULT_THRESHOLD_MULTIPLIER = 1.5
    MIN_COUPLING_DAYS = 90  # Pflicht-Dauer fuer Refund-Anspruch

    def check_guarantee(
        self,
        hotel_id: str,
        period_start_iso: str,
        period_end_iso: str,
        profit_eur: float,
        nine_os_cost_eur: float,
        coupling_days: int,
        threshold_multiplier: float | None = None,
    ) -> GuaranteeCheck:
        """Profit-Garantie pruefen.

        Args:
            threshold_multiplier: 1.5 default (Hotelier muss 1.5x cost verdienen)
        """
        if nine_os_cost_eur < 0 or coupling_days < 0:
            raise ValueError("Negative inputs not allowed")

        mult = threshold_multiplier or self.DEFAULT_THRESHOLD_MULTIPLIER
        if mult <= 0:
            raise ValueError(f"Invalid multiplier: {mult}")

        threshold = nine_os_cost_eur * mult
        guarantee_met = profit_eur >= threshold

        # Refund-Eligibility: nur wenn Garantie verfehlt UND Coupling >= 90 Tage
        refund_eligible = (not guarantee_met) and (coupling_days >= self.MIN_COUPLING_DAYS)

        # Refund-Berechnung: 9OS-Cost minus erreichter Profit (positiv)
        refund_eur = 0.0
        if refund_eligible:
            shortfall = threshold - profit_eur
            # Refund max = 9OS-Cost (kein Hotelier-Verlust ueber 9OS-Kosten hinaus)
            refund_eur = round(min(shortfall, nine_os_cost_eur), 2)

        return GuaranteeCheck(
            hotel_id=hotel_id,
            period_start_iso=period_start_iso,
            period_end_iso=period_end_iso,
            profit_eur=round(profit_eur, 2),
            nine_os_cost_eur=round(nine_os_cost_eur, 2),
            threshold_eur=round(threshold, 2),
            threshold_multiplier=mult,
            guarantee_met=guarantee_met,
            coupling_days=coupling_days,
            refund_eligible=refund_eligible,
            refund_eur=refund_eur,
            check_ts=time.time(),
        )

    def trigger_refund(self, check: GuaranteeCheck) -> dict:
        """Refund triggern (K_0: PHRONESIS_TICKET Pflicht).

        Returns: Refund-Action-Dict (kein direkter Charge - nur Trigger-Signal).
        """
        if not check.refund_eligible:
            return {"triggered": False, "reason": "not_eligible"}

        # K_0-Schutz: PHRONESIS_TICKET Pflicht
        if not os.environ.get("PHRONESIS_TICKET"):
            return {
                "triggered": False,
                "reason": "phronesis_ticket_required",
                "message": "K_0-Pflicht-Phronesis Martin: Profit-Garantie-Refund erfordert Approval",
            }

        return {
            "triggered": True,
            "hotel_id": check.hotel_id,
            "refund_eur": check.refund_eur,
            "period": f"{check.period_start_iso} → {check.period_end_iso}",
            "phronesis_ticket": os.environ.get("PHRONESIS_TICKET", "MISSING"),
            "trigger_ts": time.time(),
        }
