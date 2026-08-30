from datetime import datetime, timedelta
from src.compliance.guard import RBIComplianceGuard
from src.models.schemas import (
    FailedPaymentEvent,
    DecisionAction,
    MerchantCategory,
)


def make_event(**overrides) -> FailedPaymentEvent:
    defaults = {
        "subscription_id": "sub_test_001",
        "customer_id": "cust_test_001",
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


def test_revoke_mandate_blocks():
    guard = RBIComplianceGuard()
    event = make_event()
    history = make_history(mandate_revoked=True)
    d = guard.check(event, history)
    assert not d.allowed
    assert d.action == DecisionAction.STOP
    assert "revoked" in d.reason.lower()


def test_24h_notice_blocks():
    guard = RBIComplianceGuard()
    event = make_event()
    history = make_history(last_attempt=datetime.now() - timedelta(hours=10))
    d = guard.check(event, history)
    assert not d.allowed
    assert d.action == DecisionAction.STOP
    assert "24h" in d.reason


def test_24h_notice_allows_after_window():
    guard = RBIComplianceGuard()
    event = make_event()
    history = make_history(last_attempt=datetime.now() - timedelta(hours=25))
    d = guard.check(event, history)
    assert d.allowed
    assert d.action == DecisionAction.SCHEDULE_RETRY


def test_amount_below_threshold_allows():
    guard = RBIComplianceGuard()
    event = make_event(amount=14999)
    d = guard.check(event, make_history())
    assert d.allowed


def test_amount_exactly_at_threshold_allows():
    guard = RBIComplianceGuard()
    event = make_event(amount=15000)
    d = guard.check(event, make_history())
    assert d.allowed


def test_amount_above_threshold_blocks():
    guard = RBIComplianceGuard()
    event = make_event(amount=15001)
    d = guard.check(event, make_history())
    assert not d.allowed
    assert d.action == DecisionAction.STEP_UP_LINK


def test_insurance_higher_threshold():
    guard = RBIComplianceGuard()
    event = make_event(amount=50000, merchant_category=MerchantCategory.INSURANCE)
    d = guard.check(event, make_history())
    assert d.allowed


def test_insurance_above_1l_blocks():
    guard = RBIComplianceGuard()
    event = make_event(amount=100001, merchant_category=MerchantCategory.INSURANCE)
    d = guard.check(event, make_history())
    assert not d.allowed
    assert d.action == DecisionAction.STEP_UP_LINK


def test_max_retries_blocks():
    guard = RBIComplianceGuard()
    event = make_event()
    history = make_history(retry_count_last_7d=3)
    d = guard.check(event, history)
    assert not d.allowed
    assert d.action == DecisionAction.STOP
    assert "max retries" in d.reason.lower()


def test_retries_under_limit_allows():
    guard = RBIComplianceGuard()
    event = make_event()
    history = make_history(retry_count_last_7d=2)
    d = guard.check(event, history)
    assert d.allowed
