import os
import pickle
import numpy as np
from src.models.schemas import FailedPaymentEvent, FailureCode, MerchantCategory
from src.ai.predictor import heuristic_predict

FAILURE_CODE_MAP = {fc.value: i for i, fc in enumerate(FailureCode)}
CATEGORY_MAP = {c.value: i for i, c in enumerate(MerchantCategory)}
BANK_MAP = {"SBI": 0, "HDFC": 1, "ICICI": 2, "AXIS": 3, "KOTAK": 4, "PNB": 5, "BOB": 6}
DELAY_BUCKETS = {0: 0, 1: 1, 2: 4, 3: 8, 4: 16}

ML_MODEL = None
DELAY_MODEL = None


def _load_models():
    global ML_MODEL, DELAY_MODEL
    success_path = "models/success_model.pkl"
    delay_path = "models/delay_model.pkl"
    if os.path.exists(success_path) and os.path.exists(delay_path):
        with open(success_path, "rb") as f:
            ML_MODEL = pickle.load(f)
        with open(delay_path, "rb") as f:
            DELAY_MODEL = pickle.load(f)


def ml_predict(event: FailedPaymentEvent) -> dict:
    if ML_MODEL is None:
        _load_models()
    if ML_MODEL is None:
        return heuristic_predict(event)

    try:
        features = np.array([[
            event.amount,
            FAILURE_CODE_MAP.get(event.failure_code.value, 0),
            CATEGORY_MAP.get(event.merchant_category.value, 5),
            event.timestamp.hour,
            event.timestamp.day,
            event.previous_success_count,
            event.previous_failure_count,
            getattr(event, "attempt_count", 1),
            30,
            BANK_MAP.get(event.bank, 0) if event.bank else 0,
        ]])

        success_prob = ML_MODEL.predict_proba(features)[0][1]
        delay_bucket = DELAY_MODEL.predict(features)[0]
        delay_hours = DELAY_BUCKETS.get(int(delay_bucket), 4)

        if success_prob < 0.2:
            return {
                "recommended_action": "NO_RETRY",
                "delay_hours": 0,
                "confidence": round(success_prob, 2),
                "reason": f"ML model low success probability ({success_prob:.0%})",
            }

        return {
            "recommended_action": "RETRY",
            "delay_hours": delay_hours,
            "confidence": round(success_prob, 2),
            "reason": f"ML model predicts {success_prob:.0%} success with {delay_hours}h delay",
        }
    except Exception:
        return heuristic_predict(event)
