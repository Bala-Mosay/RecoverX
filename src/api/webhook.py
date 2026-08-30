import hashlib
import hmac
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")


def verify_webhook_signature(payload_body: bytes, signature: str) -> bool:
    if not RAZORPAY_WEBHOOK_SECRET:
        logger.warning("Webhook secret not configured, skipping verification")
        return True

    expected = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        payload_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def parse_webhook_event(event_data: dict) -> dict:
    event_type = event_data.get("event", "")
    payload = event_data.get("payload", {})

    subscription_data = payload.get("subscription", {}).get("payload", {})
    payment_data = payload.get("payment", {}).get("payload", {})

    result = {
        "event_type": event_type,
        "subscription_id": subscription_data.get("id", ""),
        "subscription_status": subscription_data.get("status", ""),
        "customer_id": subscription_data.get("customer_id", ""),
        "payment_id": payment_data.get("id", ""),
        "payment_status": payment_data.get("status", ""),
        "amount": payment_data.get("amount", 0),
        "currency": payment_data.get("currency", "INR"),
        "error_code": payment_data.get("error_code", ""),
        "error_description": payment_data.get("error_description", ""),
        "timestamp": datetime.now().isoformat(),
    }

    return result


FAILURE_CODE_MAP = {
    "INSUFFICIENT_FUNDS": "INSUFFICIENT_FUNDS",
    "NETWORK_ERROR": "NETWORK_ERROR",
    "technical_error": "TECHNICAL_ERROR",
    "payment_failed": "PAYMENT_FAILED",
    "CARD_EXPIRED": "CARD_EXPIRED",
    "AUTHENTICATION_FAILED": "AUTHENTICATION_FAILED",
    "bank_declined": "BANK_DECLINED",
    "LIMIT_EXCEEDED": "LIMIT_EXCEEDED",
    "MANDATE_NOT_FOUND": "MANDATE_NOT_FOUND",
}


def map_error_code(rzpay_error: str) -> str:
    return FAILURE_CODE_MAP.get(rzpay_error, "UNKNOWN")
