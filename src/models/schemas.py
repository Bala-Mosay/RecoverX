from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class FailureCode(str, Enum):
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    NETWORK_ERROR = "NETWORK_ERROR"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    CARD_EXPIRED = "CARD_EXPIRED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    MANDATE_NOT_FOUND = "MANDATE_NOT_FOUND"
    BANK_DECLINED = "BANK_DECLINED"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    UNKNOWN = "UNKNOWN"


class MerchantCategory(str, Enum):
    SAAS = "SAAS"
    INSURANCE = "INSURANCE"
    MUTUAL_FUND_SIP = "MUTUAL_FUND_SIP"
    CREDIT_CARD_BILL = "CREDIT_CARD_BILL"
    OTT_PLATFORM = "OTT_PLATFORM"
    ECOMMERCE = "ECOMMERCE"
    OTHER = "OTHER"


class FailedPaymentEvent(BaseModel):
    subscription_id: str
    customer_id: str
    amount: int = Field(description="Amount in paise")
    currency: str = "INR"
    failure_code: FailureCode
    merchant_category: MerchantCategory = MerchantCategory.OTHER
    timestamp: datetime = Field(default_factory=datetime.now)
    attempt_count: int = 1
    last_attempt: Optional[datetime] = None
    bank: str = ""
    previous_success_count: int = 0
    previous_failure_count: int = 0


class DecisionAction(str, Enum):
    SCHEDULE_RETRY = "SCHEDULE_RETRY"
    STEP_UP_LINK = "STEP_UP_LINK"
    STOP = "STOP"


class ComplianceDecision(BaseModel):
    allowed: bool
    action: DecisionAction
    reason: str
    requires_customer_action: bool = False
    next_allowed_at: Optional[datetime] = None

    def __repr__(self) -> str:
        return (
            f"ComplianceDecision(allowed={self.allowed}, action={self.action.value}, "
            f"reason='{self.reason}', requires_customer_action={self.requires_customer_action})"
        )


class AuditLogEntry(BaseModel):
    event_id: str
    subscription_id: str
    customer_id: str
    amount: int
    failure_code: str
    ai_recommendation: Optional[str] = None
    compliance_decision: Optional[str] = None
    action_taken: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    outcome: str = "pending"
