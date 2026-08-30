from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class RazorpayWebhookPayload(BaseModel):
    entity: str = ""
    event: str = ""
    payload: dict = {}
    created_at: Optional[int] = None


class SubscriptionPayload(BaseModel):
    id: str
    entity: str = "subscription"
    status: str = ""
    plan_id: str = ""
    customer_id: str = ""
    current_start: Optional[int] = None
    charge_at: Optional[int] = None
    end: Optional[int] = None


class PaymentPayload(BaseModel):
    id: str
    entity: str = "payment"
    status: str = ""
    amount: int = 0
    currency: str = "INR"
    order_id: str = ""
    method: str = ""
    error_code: str = ""
    error_description: str = ""
