import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from typing import Optional

from src.api.webhook import verify_webhook_signature, parse_webhook_event, map_error_code
from src.models.schemas import FailedPaymentEvent, FailureCode, MerchantCategory
from src.compliance.guard import RBIComplianceGuard
from src.ai.predictor import heuristic_predict
from src.integration.razorpay import RazorpayClient
from src.integration.notify import MockWhatsAppAdapter
from src.models.database import SessionLocal, PaymentEventRecord, ComplianceRecord, RetryRecord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook_server")

app = FastAPI(
    title="MandateMind API",
    description="AI-Powered Payment Recovery Engine with RBI Compliance",
    version="1.0.0",
)

guard = RBIComplianceGuard()
razorpay = RazorpayClient(test_mode=True)
whatsapp = MockWhatsAppAdapter()
history = {}
retry_timestamps = {}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "MandateMind",
    }


@app.post("/webhook/razorpay")
async def razorpay_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not verify_webhook_signature(body, signature):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        event_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    parsed = parse_webhook_event(event_data)
    logger.info("Webhook received: %s for subscription %s", parsed["event_type"], parsed["subscription_id"])

    event_type = parsed["event_type"]

    if event_type in ("subscription.pending", "subscription.charged_failed"):
        return await handle_payment_failure(parsed)
    elif event_type == "subscription.charged":
        return await handle_payment_success(parsed)
    elif event_type == "subscription.halted":
        return await handle_subscription_halted(parsed)
    elif event_type == "subscription.cancelled":
        return await handle_subscription_cancelled(parsed)
    else:
        logger.info("Ignoring event type: %s", event_type)
        return {"status": "ignored", "event_type": event_type}


async def handle_payment_failure(parsed: dict) -> dict:
    subscription_id = parsed["subscription_id"]
    customer_id = parsed["customer_id"]
    amount = parsed["amount"]
    error_code = parsed["error_code"]

    failure_code_str = map_error_code(error_code)
    try:
        failure_code = FailureCode(failure_code_str)
    except ValueError:
        failure_code = FailureCode.UNKNOWN

    event = FailedPaymentEvent(
        subscription_id=subscription_id,
        customer_id=customer_id,
        amount=amount,
        failure_code=failure_code,
        merchant_category=MerchantCategory.SAAS,
        timestamp=datetime.now(),
        bank="",
    )

    h = history.get(subscription_id, {"last_attempt": None, "retry_count_last_7d": 0, "mandate_revoked": False})
    ai_rec = heuristic_predict(event)
    decision = guard.check(event, h, retry_timestamps.get(subscription_id))

    db = SessionLocal()
    try:
        event_id = f"EVT_{int(datetime.now().timestamp())}"

        db.add(PaymentEventRecord(
            id=event_id,
            subscription_id=subscription_id,
            customer_id=customer_id,
            amount=amount,
            failure_code=failure_code_str,
            merchant_category="SAAS",
            timestamp=datetime.now(),
        ))

        db.add(ComplianceRecord(
            id=f"COMP_{event_id}",
            event_id=event_id,
            subscription_id=subscription_id,
            allowed=decision.allowed,
            action=decision.action.value,
            reason=decision.reason,
        ))

        action_taken = "NONE"
        if not decision.allowed:
            if decision.action.value == "STEP_UP_LINK":
                link = razorpay.create_payment_link(amount, customer_id)
                whatsapp.send("stepup_link", customer_id=customer_id, amount=amount, payment_url=link.get("url", ""))
                action_taken = "STEP_UP_LINK_SENT"
            else:
                action_taken = "STOPPED"
        else:
            action_taken = "RETRY_SCHEDULED"
            h["last_attempt"] = datetime.now()
            h["retry_count_last_7d"] += 1

        db.add(RetryRecord(
            id=f"RETRY_{event_id}",
            event_id=event_id,
            subscription_id=subscription_id,
            customer_id=customer_id,
            amount=amount,
            action_taken=action_taken,
            ai_delay_hours=ai_rec["delay_hours"],
            ai_confidence=ai_rec["confidence"],
        ))

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("DB error: %s", e)
    finally:
        db.close()

    history[subscription_id] = h

    return {
        "status": "processed",
        "event_type": "payment_failure",
        "subscription_id": subscription_id,
        "compliance_allowed": decision.allowed,
        "action": decision.action.value,
        "reason": decision.reason,
    }


async def handle_payment_success(parsed: dict) -> dict:
    logger.info("Payment success for subscription %s", parsed["subscription_id"])
    return {"status": "processed", "event_type": "payment_success"}


async def handle_subscription_halted(parsed: dict) -> dict:
    logger.info("Subscription halted: %s", parsed["subscription_id"])
    return {"status": "processed", "event_type": "subscription_halted"}


async def handle_subscription_cancelled(parsed: dict) -> dict:
    sub_id = parsed["subscription_id"]
    if sub_id in history:
        history[sub_id]["mandate_revoked"] = True
    logger.info("Subscription cancelled: %s", sub_id)
    return {"status": "processed", "event_type": "subscription_cancelled"}


@app.get("/metrics")
async def get_metrics():
    db = SessionLocal()
    try:
        from sqlalchemy import func
        total_events = db.query(func.count(PaymentEventRecord.id)).scalar() or 0
        total_compliance = db.query(func.count(ComplianceRecord.id)).scalar() or 0
        allowed = db.query(func.count(ComplianceRecord.id)).filter(ComplianceRecord.allowed == True).scalar() or 0
        blocked = total_compliance - allowed

        return {
            "total_events": total_events,
            "total_compliance_decisions": total_compliance,
            "allowed": allowed,
            "blocked": blocked,
            "recovery_rate": round((allowed / total_events * 100), 1) if total_events > 0 else 0,
        }
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
