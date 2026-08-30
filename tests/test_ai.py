from src.ai.predictor import heuristic_predict, ml_predict
from src.models.schemas import FailedPaymentEvent, FailureCode, MerchantCategory


def make_event(**overrides) -> FailedPaymentEvent:
    defaults = {
        "subscription_id": "sub_test",
        "customer_id": "cust_test",
        "amount": 5000,
        "failure_code": FailureCode.INSUFFICIENT_FUNDS,
        "merchant_category": MerchantCategory.SAAS,
        "previous_success_count": 5,
    }
    defaults.update(overrides)
    return FailedPaymentEvent(**defaults)


def test_insufficient_funds_delays_6h():
    event = make_event(failure_code=FailureCode.INSUFFICIENT_FUNDS)
    result = heuristic_predict(event)
    assert result["recommended_action"] == "RETRY"
    assert result["delay_hours"] == 6


def test_network_error_delays_1h():
    event = make_event(failure_code=FailureCode.NETWORK_ERROR)
    result = heuristic_predict(event)
    assert result["recommended_action"] == "RETRY"
    assert result["delay_hours"] == 1


def test_card_expired_no_retry():
    event = make_event(failure_code=FailureCode.CARD_EXPIRED)
    result = heuristic_predict(event)
    assert result["recommended_action"] == "NO_RETRY"
    assert result["delay_hours"] == 0


def test_auth_failed_no_retry():
    event = make_event(failure_code=FailureCode.AUTHENTICATION_FAILED)
    result = heuristic_predict(event)
    assert result["recommended_action"] == "NO_RETRY"


def test_high_success_history_boosts_confidence():
    event_high = make_event(previous_success_count=10)
    event_low = make_event(previous_success_count=1)
    r_high = heuristic_predict(event_high)
    r_low = heuristic_predict(event_low)
    assert r_high["confidence"] > r_low["confidence"]


def test_ml_predict_falls_back_to_heuristic():
    event = make_event(failure_code=FailureCode.BANK_DECLINED)
    result = ml_predict(event)
    assert result["recommended_action"] == "RETRY"
    assert result["delay_hours"] == 8


def test_output_has_required_keys():
    event = make_event()
    result = heuristic_predict(event)
    assert "recommended_action" in result
    assert "delay_hours" in result
    assert "confidence" in result
    assert "reason" in result
