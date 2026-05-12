# DF-HeyLou-9OS-Coupling-Validator [CRUX-MK]

**Welle-40 Profit-Layer #4: Profit-Garantie HeyLou+9OS-NEXT Coupling.**

Per Martin-Direktive: *"die APP ist dann fuer den Hotellier interessant wenn er mit HeyLou auch 9OS enthaelt und sein Hotel dann Gewinn macht"*.

## Status
- Version: 0.1.0-SKELETON
- Phase: PRE-PRODUCTION-CONDITIONAL
- **K_0-Touch: TRUE (Profit-Garantie + Refund-Mechanik)**

## Architektur
```
src/
├── coupling_validator.py    # Cross-DF-Health-Check + Profit-Tracker
├── profit_calculator.py      # Direct-Revenue + Anti-OTA-Savings - 9OS-Cost
├── guarantee_engine.py       # Profit-Garantie-Logic + Refund-Mechanik
├── validator_orchestrator.py
└── audit_logger.py
```

## Profit-Garantie-Formel
```
profit_eur = direct_booking_revenue + avoided_ota_commission - 9os_subscription_cost
guarantee_met = profit_eur >= threshold (default: 9os_cost * 1.5)
refund_due = guarantee_met == False AND coupling_period >= 90 Tage
```

## K_0-Schutz
- Refund-Mechanik nur via PHRONESIS_TICKET (Martin-Approval)
- Profit-Tracker deterministisch, kein LLM
- Audit-Chain-Pflicht pro Profit-Snapshot

[CRUX-MK]
