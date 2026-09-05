import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "RecoverX"
    assert "timestamp" in data


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_events" in data
    assert "total_compliance_decisions" in data
    assert "allowed" in data
    assert "blocked" in data
    assert "recovery_rate" in data


def test_webhook_payment_failure():
    payload = {
        "event": "subscription.charged_failed",
        "payload": {
            "subscription": {
                "payload": {
                    "id": "sub_test_001",
                    "status": "active",
                    "customer_id": "cust_test_001",
                }
            },
            "payment": {
                "payload": {
                    "id": "pay_test_001",
                    "status": "failed",
                    "amount": 249900,
                    "currency": "INR",
                    "error_code": "INSUFFICIENT_FUNDS",
                    "error_description": "Insufficient funds",
                }
            },
        },
    }
    response = client.post(
        "/webhook/razorpay",
        json=payload,
        headers={"X-Razorpay-Signature": "test_sig"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processed"
    assert data["event_type"] == "payment_failure"
    assert data["subscription_id"] == "sub_test_001"


def test_webhook_payment_success():
    payload = {
        "event": "subscription.charged",
        "payload": {
            "subscription": {
                "payload": {
                    "id": "sub_test_002",
                    "status": "active",
                    "customer_id": "cust_test_002",
                }
            },
            "payment": {
                "payload": {
                    "id": "pay_test_002",
                    "status": "captured",
                    "amount": 150000,
                    "currency": "INR",
                }
            },
        },
    }
    response = client.post(
        "/webhook/razorpay",
        json=payload,
        headers={"X-Razorpay-Signature": "test_sig"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processed"
    assert data["event_type"] == "payment_success"


def test_webhook_subscription_cancelled():
    payload = {
        "event": "subscription.cancelled",
        "payload": {
            "subscription": {
                "payload": {
                    "id": "sub_test_003",
                    "status": "cancelled",
                    "customer_id": "cust_test_003",
                }
            },
            "payment": {"payload": {}},
        },
    }
    response = client.post(
        "/webhook/razorpay",
        json=payload,
        headers={"X-Razorpay-Signature": "test_sig"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processed"
    assert data["event_type"] == "subscription_cancelled"


def test_webhook_ignored_event():
    payload = {
        "event": "subscription.activated",
        "payload": {
            "subscription": {
                "payload": {
                    "id": "sub_test_004",
                    "status": "active",
                    "customer_id": "cust_test_004",
                }
            },
            "payment": {"payload": {}},
        },
    }
    response = client.post(
        "/webhook/razorpay",
        json=payload,
        headers={"X-Razorpay-Signature": "test_sig"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ignored"
    assert data["event_type"] == "subscription.activated"


def test_webhook_invalid_json():
    response = client.post(
        "/webhook/razorpay",
        content="not json",
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": "test_sig",
        },
    )
    assert response.status_code == 400


def test_webhook_high_amount_blocks():
    payload = {
        "event": "subscription.charged_failed",
        "payload": {
            "subscription": {
                "payload": {
                    "id": "sub_test_high",
                    "status": "active",
                    "customer_id": "cust_test_high",
                }
            },
            "payment": {
                "payload": {
                    "id": "pay_test_high",
                    "status": "failed",
                    "amount": 2500000,
                    "currency": "INR",
                    "error_code": "INSUFFICIENT_FUNDS",
                    "error_description": "Insufficient funds",
                }
            },
        },
    }
    response = client.post(
        "/webhook/razorpay",
        json=payload,
        headers={"X-Razorpay-Signature": "test_sig"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["compliance_allowed"] is False
    assert data["action"] == "STEP_UP_LINK"
