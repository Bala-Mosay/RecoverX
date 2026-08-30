from datetime import datetime, timedelta
from typing import Optional, List
from src.models.schemas import (
    FailedPaymentEvent,
    ComplianceDecision,
    DecisionAction,
)


DEFAULT_CONFIG = {
    "standard_limit": 15000,
    "enhanced_limit": 100000,
    "high_value_categories": ["INSURANCE", "MUTUAL_FUND_SIP", "CREDIT_CARD_BILL"],
    "max_retries": 3,
    "pre_debit_notice_hours": 24,
    "retry_window_days": 7,
}


class RBIComplianceGuard:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or DEFAULT_CONFIG

    def _count_retries_in_window(
        self, retry_timestamps: List[datetime], window_days: int = 7
    ) -> int:
        cutoff = datetime.now() - timedelta(days=window_days)
        return sum(1 for ts in retry_timestamps if ts > cutoff)

    def _get_applicable_threshold(self, merchant_category: str) -> int:
        if merchant_category in self.config["high_value_categories"]:
            return self.config["enhanced_limit"]
        return self.config["standard_limit"]

    def check(
        self,
        event: FailedPaymentEvent,
        payment_history: dict,
        retry_timestamps: Optional[List[datetime]] = None,
    ) -> ComplianceDecision:
        now = datetime.now()

        if payment_history.get("mandate_revoked", False):
            return ComplianceDecision(
                allowed=False,
                action=DecisionAction.STOP,
                reason="Mandate revoked by customer",
                requires_customer_action=True,
            )

        last_attempt = payment_history.get("last_attempt")
        if isinstance(last_attempt, datetime) and now < last_attempt + timedelta(
            hours=self.config["pre_debit_notice_hours"]
        ):
            next_allowed = last_attempt + timedelta(
                hours=self.config["pre_debit_notice_hours"]
            )
            return ComplianceDecision(
                allowed=False,
                action=DecisionAction.STOP,
                reason=f"24h pre-debit notification not yet satisfied. Retry after {next_allowed}",
                requires_customer_action=False,
                next_allowed_at=next_allowed,
            )

        threshold = self._get_applicable_threshold(event.merchant_category.value)
        if event.amount > threshold:
            return ComplianceDecision(
                allowed=False,
                action=DecisionAction.STEP_UP_LINK,
                reason=f"Amount {event.amount} exceeds threshold {threshold} for category {event.merchant_category.value}",
                requires_customer_action=True,
            )

        if retry_timestamps is None:
            attempts = payment_history.get("retry_count_last_7d", 0)
        else:
            attempts = self._count_retries_in_window(
                retry_timestamps, self.config["retry_window_days"]
            )

        if attempts >= self.config["max_retries"]:
            return ComplianceDecision(
                allowed=False,
                action=DecisionAction.STOP,
                reason=f"Max retries ({self.config['max_retries']}) reached within {self.config['retry_window_days']}-day window",
                requires_customer_action=False,
            )

        return ComplianceDecision(
            allowed=True,
            action=DecisionAction.SCHEDULE_RETRY,
            reason="All compliance checks passed",
            requires_customer_action=False,
        )
