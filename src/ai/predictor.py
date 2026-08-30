from typing import Optional
from src.models.schemas import FailedPaymentEvent, FailureCode


HEURISTIC_RULES = {
    FailureCode.INSUFFICIENT_FUNDS: {
        "delay_hours": 6,
        "reason": "Insufficient funds — retry in evening when salary may credit",
    },
    FailureCode.NETWORK_ERROR: {
        "delay_hours": 1,
        "reason": "Network issue — quick retry likely to succeed",
    },
    FailureCode.TECHNICAL_ERROR: {
        "delay_hours": 2,
        "reason": "Technical error on bank side — retry after short cooldown",
    },
    FailureCode.PAYMENT_FAILED: {
        "delay_hours": 4,
        "reason": "Generic payment failure — retry after a few hours",
    },
    FailureCode.CARD_EXPIRED: {
        "delay_hours": 0,
        "reason": "Card expired — no point retrying automatically",
    },
    FailureCode.AUTHENTICATION_FAILED: {
        "delay_hours": 0,
        "reason": "Auth failure — requires customer action",
    },
    FailureCode.BANK_DECLINED: {
        "delay_hours": 8,
        "reason": "Bank declined — retry later in the day",
    },
    FailureCode.LIMIT_EXCEEDED: {
        "delay_hours": 12,
        "reason": "Daily limit exceeded — retry next day",
    },
    FailureCode.MANDATE_NOT_FOUND: {
        "delay_hours": 0,
        "reason": "Mandate not found — cannot retry automatically",
    },
    FailureCode.UNKNOWN: {
        "delay_hours": 4,
        "reason": "Unknown error — moderate delay before retry",
    },
}


def heuristic_predict(event: FailedPaymentEvent) -> dict:
    rule = HEURISTIC_RULES.get(event.failure_code, HEURISTIC_RULES[FailureCode.UNKNOWN])

    if rule["delay_hours"] == 0:
        return {
            "recommended_action": "NO_RETRY",
            "delay_hours": 0,
            "confidence": 0.9,
            "reason": rule["reason"],
        }

    confidence = 0.7
    if event.previous_success_count > 3:
        confidence = min(0.9, confidence + 0.1 * (event.previous_success_count - 3))

    return {
        "recommended_action": "RETRY",
        "delay_hours": rule["delay_hours"],
        "confidence": round(confidence, 2),
        "reason": rule["reason"],
    }


def ml_predict(event: FailedPaymentEvent, model=None) -> dict:
    if model is None:
        return heuristic_predict(event)
    return heuristic_predict(event)
