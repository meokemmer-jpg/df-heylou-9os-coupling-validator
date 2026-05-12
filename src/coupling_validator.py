"""Coupling-Validator [CRUX-MK].

Cross-DF-Health-Check zwischen HeyLou + 9OS-NEXT per coupled-Hotel.

K_0-Pflicht: KEIN LLM, deterministische Health-Aggregation.

[CRUX-MK]
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CouplingHealthStatus(str, Enum):
    HEALTHY = "healthy"          # Beide DFs OK
    DEGRADED_HEYLOU = "degraded_heylou"
    DEGRADED_9OS = "degraded_9os"
    BOTH_DEGRADED = "both_degraded"
    NOT_COUPLED = "not_coupled"


@dataclass
class CouplingState:
    """State des Couplings pro Hotel."""
    hotel_id: str
    heylou_active: bool
    nine_os_active: bool
    coupling_start_iso: str
    last_health_check_ts: float = field(default_factory=time.time)
    consecutive_unhealthy_checks: int = 0

    @property
    def status(self) -> CouplingHealthStatus:
        if not self.heylou_active and not self.nine_os_active:
            return CouplingHealthStatus.NOT_COUPLED
        if self.heylou_active and not self.nine_os_active:
            return CouplingHealthStatus.DEGRADED_9OS
        if not self.heylou_active and self.nine_os_active:
            return CouplingHealthStatus.DEGRADED_HEYLOU
        return CouplingHealthStatus.HEALTHY


class CouplingValidator:
    """Validator fuer HeyLou+9OS Coupling-State."""

    def __init__(self):
        self._states: dict[str, CouplingState] = {}

    def register_coupling(
        self,
        hotel_id: str,
        coupling_start_iso: str,
        heylou_active: bool = True,
        nine_os_active: bool = True,
    ) -> CouplingState:
        s = CouplingState(
            hotel_id=hotel_id,
            heylou_active=heylou_active,
            nine_os_active=nine_os_active,
            coupling_start_iso=coupling_start_iso,
        )
        self._states[hotel_id] = s
        return s

    def update_health(
        self,
        hotel_id: str,
        heylou_active: bool,
        nine_os_active: bool,
    ) -> CouplingState:
        if hotel_id not in self._states:
            raise KeyError(f"No coupling registered: {hotel_id}")
        s = self._states[hotel_id]
        s.heylou_active = heylou_active
        s.nine_os_active = nine_os_active
        s.last_health_check_ts = time.time()
        if s.status != CouplingHealthStatus.HEALTHY:
            s.consecutive_unhealthy_checks += 1
        else:
            s.consecutive_unhealthy_checks = 0
        return s

    def get_state(self, hotel_id: str) -> Optional[CouplingState]:
        return self._states.get(hotel_id)
