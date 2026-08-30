from datetime import datetime, timedelta
from src.compliance.guard import RBIComplianceGuard
from src.models.schemas import FailedPaymentEvent, DecisionAction, MerchantCategory


def make_event(**overrides) -> FailedPaymentEvent:
    defaults = {
        "subscription_id": "sub_edge",
        "customer_id": "cust_edge",
        "amount": 5000,
        "failure_code": "INSUFFICIENT_FUNDS",
        "merchant_category": MerchantCategory.SAAS,
    }
    defaults.update(overrides)
    return FailedPaymentEvent(**defaults)


def make_history(**overrides) -> dict:
    defaults = {"last_attempt": None, "retry_count_last_7d": 0, "mandate_revoked": False}
    defaults.update(overrides)
    return defaults


def test_exactly_24h_boundary():
    guard = RBIComplianceGuard()
    event = make_event()
    last = datetime.now() - timedelta(hours=24)
    d = guard.check(event, make_history(last_attempt=last))
    assert d.allowed, f"Should allow at exactly 24h, got {d}"


def test_one_minute_before_24h_blocks():
    guard = RBIComplianceGuard()
    event = make_event()
    last = datetime.now() - timedelta(hours=23, minutes=59)
    d = guard.check(event, make_history(last_attempt=last))
    assert not d.allowed


def test_no_last_attempt_allows():
    guard = RBIComplianceGuard()
    event = make_event()
    d = guard.check(event, make_history())
    assert d.allowed


def test_zero_amount_allows():
    guard = RBIComplianceGuard()
    event = make_event(amount=0)
    d = guard.check(event, make_history())
    assert d.allowed


def test_sip_higher_threshold():
    guard = RBIComplianceGuard()
    event = make_event(amount=80000, merchant_category=MerchantCategory.MUTUAL_FUND_SIP)
    d = guard.check(event, make_history())
    assert d.allowed


def test_credit_card_higher_threshold():
    guard = RBIComplianceGuard()
    event = make_event(amount=90000, merchant_category=MerchantCategory.CREDIT_CARD_BILL)
    d = guard.check(event, make_history())
    assert d.allowed


def test_two_retries_allows():
    guard = RBIComplianceGuard()
    event = make_event()
    d = guard.check(event, make_history(retry_count_last_7d=2))
    assert d.allowed


def test_three_retries_blocks():
    guard = RBIComplianceGuard()
    event = make_event()
    d = guard.check(event, make_history(retry_count_last_7d=3))
    assert not d.allowed


def test_revoked_always_blocks():
    guard = RBIComplianceGuard()
    event = make_event(amount=100)
    d = guard.check(event, make_history(mandate_revoked=True))
    assert not d.allowed
    assert d.action == DecisionAction.STOP


def test_high_amount_non_insurance_blocks():
    guard = RBIComplianceGuard()
    event = make_event(amount=50000, merchant_category=MerchantCategory.ECOMMERCE)
    d = guard.check(event, make_history())
    assert not d.allowed
    assert d.action == DecisionAction.STEP_UP_LINK
