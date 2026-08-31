import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

RAZORPAY_KEY = os.environ.get("RAZORPAY_TEST_KEY", "")
RAZORPAY_SECRET = os.environ.get("RAZORPAY_TEST_SECRET", "")


class RazorpayClient:
    def __init__(self, test_mode: bool = True):
        self.test_mode = test_mode
        self.api_key = RAZORPAY_KEY
        self.api_secret = RAZORPAY_SECRET
        self.client = None

        if self.api_key and self.api_secret:
            try:
                import razorpay
                self.client = razorpay.Client(auth=(self.api_key, self.api_secret))
                logger.info("Razorpay SDK initialized (test_mode=%s)", test_mode)
            except ImportError:
                logger.warning("razorpay package not installed, using stub mode")
            except Exception as e:
                logger.error("Razorpay SDK init failed: %s", e)
        else:
            logger.warning("Razorpay keys not configured, using stub mode")

    def charge_subscription(self, subscription_id: str, amount: int = 0) -> dict:
        if self.client:
            try:
                subscription = self.client.subscription.fetch(subscription_id)
                invoice_id = subscription.get("latest_invoice")
                if invoice_id:
                    invoice = self.client.invoice.fetch(invoice_id)
                    payment = self.client.payment.fetch(invoice["payment_id"])
                    return {
                        "status": "charged" if payment["status"] == "captured" else "pending",
                        "subscription_id": subscription_id,
                        "payment_id": payment["id"],
                        "amount": amount,
                        "mode": "test" if self.test_mode else "live",
                        "timestamp": datetime.now().isoformat(),
                    }
            except Exception as e:
                logger.warning("Razorpay charge failed (using stub): %s", e)

        return {
            "status": "scheduled",
            "subscription_id": subscription_id,
            "amount": amount,
            "mode": "test" if self.test_mode else "live",
            "timestamp": datetime.now().isoformat(),
            "message": f"[STUB] Retry scheduled for subscription {subscription_id}",
        }

    def create_payment_link(
        self, amount: int, customer_id: str, currency: str = "INR"
    ) -> dict:
        if self.client:
            try:
                response = self.client.payment_link.create({
                    "amount": amount,
                    "currency": currency,
                    "customer_id": customer_id,
                    "notify": {"sms": True, "email": True},
                    "callback_url": "https://your-callback-url.com",
                    "callback_method": "get",
                })
                return {
                    "link_id": response["id"],
                    "amount": amount,
                    "currency": currency,
                    "customer_id": customer_id,
                    "status": response["status"],
                    "url": response["short_url"],
                    "mode": "test" if self.test_mode else "live",
                }
            except Exception as e:
                logger.warning("Razorpay payment link failed (using stub): %s", e)

        link_id = f"plink_test_{customer_id}_{int(datetime.now().timestamp())}"
        return {
            "link_id": link_id,
            "amount": amount,
            "currency": currency,
            "customer_id": customer_id,
            "status": "created",
            "url": f"https://rzp.io/i/{link_id}",
            "mode": "test" if self.test_mode else "live",
            "message": f"[STUB] Payment link created for customer {customer_id}",
        }

    def cancel_subscription(self, subscription_id: str) -> dict:
        if self.client:
            try:
                self.client.subscription.cancel(subscription_id)
                return {
                    "status": "cancelled",
                    "subscription_id": subscription_id,
                    "mode": "test" if self.test_mode else "live",
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as e:
                logger.warning("Razorpay cancel failed (using stub): %s", e)

        return {
            "status": "cancelled",
            "subscription_id": subscription_id,
            "mode": "test" if self.test_mode else "live",
            "timestamp": datetime.now().isoformat(),
            "message": f"[STUB] Subscription {subscription_id} cancelled",
        }


RazorpayStub = RazorpayClient
