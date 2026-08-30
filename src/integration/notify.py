import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MockWhatsAppAdapter:
    TEMPLATES = {
        "pre_debit_notice": {
            "title": "Pre-Debit Notice",
            "body": "Dear {customer_id}, a payment of Rs.{amount} will be debited from your account for subscription {subscription_id} on {date}. To cancel, visit {cancel_url}.",
        },
        "retry_notification": {
            "title": "Payment Retry",
            "body": "Dear {customer_id}, we will retry your payment of Rs.{amount} for {subscription_id} at {retry_time}.",
        },
        "stepup_link": {
            "title": "Action Required",
            "body": "Dear {customer_id}, your payment of Rs.{amount} requires verification. Complete payment here: {payment_url}",
        },
        "mandate_exhausted": {
            "title": "Subscription Paused",
            "body": "Dear {customer_id}, your subscription {subscription_id} has been paused after multiple payment failures. Please update your payment method.",
        },
    }

    def send(self, template: str, **kwargs) -> dict:
        if template not in self.TEMPLATES:
            return {"status": "error", "message": f"Unknown template: {template}"}

        tpl = self.TEMPLATES[template]
        body = tpl["body"].format(**kwargs) if kwargs else tpl["body"]

        payload = {
            "channel": "whatsapp",
            "template": template,
            "title": tpl["title"],
            "body": body,
            "recipient": kwargs.get("customer_id", ""),
            "timestamp": datetime.now().isoformat(),
        }

        logger.info("MOCK WhatsApp sent: %s", json.dumps(payload, indent=2))
        return {"status": "sent", "payload": payload}
