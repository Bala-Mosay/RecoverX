import random
import uuid
from datetime import datetime, timedelta
from typing import List
from faker import Faker
from src.models.schemas import FailedPaymentEvent, FailureCode, MerchantCategory

fake = Faker()
Faker.seed(42)
random.seed(42)

CUSTOMER_COUNT = 100
FAILURE_WEIGHTS = {
    FailureCode.INSUFFICIENT_FUNDS: 30,
    FailureCode.NETWORK_ERROR: 20,
    FailureCode.TECHNICAL_ERROR: 15,
    FailureCode.PAYMENT_FAILED: 15,
    FailureCode.BANK_DECLINED: 10,
    FailureCode.CARD_EXPIRED: 5,
    FailureCode.LIMIT_EXCEEDED: 3,
    FailureCode.AUTHENTICATION_FAILED: 2,
}

FAILURE_CODES = list(FAILURE_WEIGHTS.keys())
WEIGHTS = list(FAILURE_WEIGHTS.values())

CATEGORIES = [
    MerchantCategory.SAAS,
    MerchantCategory.INSURANCE,
    MerchantCategory.MUTUAL_FUND_SIP,
    MerchantCategory.OTT_PLATFORM,
    MerchantCategory.ECOMMERCE,
    MerchantCategory.OTHER,
]


def _random_amount(category: MerchantCategory) -> int:
    if category in (
        MerchantCategory.INSURANCE,
        MerchantCategory.MUTUAL_FUND_SIP,
        MerchantCategory.CREDIT_CARD_BILL,
    ):
        return random.choice(range(500, 200001, 500))
    return random.choice(range(99, 20001, 1))


def _generate_customer_profile(customer_id: str) -> dict:
    return {
        "customer_id": customer_id,
        "name": fake.name(),
        "total_payments": random.randint(1, 50),
        "failed_payments": random.randint(0, 10),
        "category": random.choice(CATEGORIES),
        "salary_day": random.choice([1, 2, 5, 10, 15, 25]),
    }


def generate_events(count: int = 200) -> List[FailedPaymentEvent]:
    customers = [
        _generate_customer_profile(f"CUST_{i:04d}") for i in range(CUSTOMER_COUNT)
    ]
    events = []
    now = datetime.now()

    for i in range(count):
        cust = random.choice(customers)
        attempt = random.randint(1, 5)
        hours_back = random.uniform(0, 48 * 7)

        event = FailedPaymentEvent(
            subscription_id=f"sub_{cust['customer_id']}_{random.randint(1, 3)}",
            customer_id=cust["customer_id"],
            amount=_random_amount(cust["category"]),
            currency="INR",
            failure_code=random.choices(FAILURE_CODES, weights=WEIGHTS, k=1)[0],
            merchant_category=cust["category"],
            timestamp=now - timedelta(hours=hours_back),
            attempt_count=attempt,
            last_attempt=now - timedelta(hours=hours_back + random.uniform(1, 24))
            if attempt > 1
            else None,
            bank=random.choice(["SBI", "HDFC", "ICICI", "AXIS", "KOTAK", "PNB", "BOB"]),
            previous_success_count=max(0, cust["total_payments"] - cust["failed_payments"]),
            previous_failure_count=cust["failed_payments"],
        )
        events.append(event)

    return sorted(events, key=lambda e: e.timestamp)


def generate_events_json(count: int = 200) -> List[dict]:
    return [e.model_dump(mode="json") for e in generate_events(count)]


if __name__ == "__main__":
    import json

    events = generate_events(200)
    print(f"Generated {len(events)} synthetic events")
    print(f"  Failure codes: { {fc.value: sum(1 for e in events if e.failure_code == fc) for fc in FailureCode} }")
    print(f"  Categories:    { {c.value: sum(1 for e in events if e.merchant_category == c) for c in CATEGORIES} }")
    print(f"\nSample event:")
    print(json.dumps(events[0].model_dump(mode="json"), indent=2, default=str))
