import os
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from faker import Faker
import random

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

FAILURE_CODES = [
    "INSUFFICIENT_FUNDS", "NETWORK_ERROR", "TECHNICAL_ERROR",
    "PAYMENT_FAILED", "CARD_EXPIRED", "AUTHENTICATION_FAILED",
    "BANK_DECLINED", "LIMIT_EXCEEDED",
]
CATEGORIES = ["SAAS", "INSURANCE", "MUTUAL_FUND_SIP", "OTT_PLATFORM", "ECOMMERCE", "OTHER"]
BANKS = ["SBI", "HDFC", "ICICI", "AXIS", "KOTAK", "PNB", "BOB"]


def _generate_synthetic_dataset(n: int = 10000) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        amount = random.choice(range(99, 200001, 1))
        failure_code = random.choice(FAILURE_CODES)
        category = random.choice(CATEGORIES)
        hour = random.randint(0, 23)
        day_of_month = random.randint(1, 28)
        prev_success = random.randint(0, 50)
        prev_fail = random.randint(0, 10)
        attempt = random.randint(1, 5)
        days_since = random.randint(1, 90)

        success_prob = 0.5
        if failure_code == "INSUFFICIENT_FUNDS":
            if hour >= 18 or hour <= 6:
                success_prob += 0.15
            if day_of_month <= 5:
                success_prob += 0.2
            if prev_success > 10:
                success_prob += 0.1
        elif failure_code == "NETWORK_ERROR":
            success_prob += 0.1
        elif failure_code in ("CARD_EXPIRED", "AUTHENTICATION_FAILED"):
            success_prob -= 0.4
        elif failure_code == "LIMIT_EXCEEDED":
            if hour < 10:
                success_prob -= 0.1
            success_prob += 0.05
        if amount > 100000:
            success_prob -= 0.15
        elif amount < 5000:
            success_prob += 0.1
        if attempt > 2:
            success_prob -= 0.15
        if prev_success > 20:
            success_prob += 0.05

        success_prob = max(0.05, min(0.95, success_prob))
        success = 1 if random.random() < success_prob else 0

        # Discretize delay into buckets: 0=immediate, 1=short(1-2h), 2=medium(3-6h), 3=long(7-12h), 4=overnight(13-24h)
        if success:
            if failure_code == "INSUFFICIENT_FUNDS":
                delay_bucket = random.choice([2, 2, 3, 3])
            elif failure_code == "NETWORK_ERROR":
                delay_bucket = random.choice([0, 1, 1])
            elif failure_code == "TECHNICAL_ERROR":
                delay_bucket = random.choice([1, 2, 2])
            elif failure_code == "BANK_DECLINED":
                delay_bucket = random.choice([2, 3, 3])
            elif failure_code == "LIMIT_EXCEEDED":
                delay_bucket = random.choice([3, 4])
            else:
                delay_bucket = random.choice([1, 2, 3])
        else:
            delay_bucket = random.choice([0, 0, 1, 2, 3, 4])

        rows.append({
            "amount": amount,
            "failure_code": FAILURE_CODES.index(failure_code),
            "category": CATEGORIES.index(category),
            "hour": hour,
            "day_of_month": day_of_month,
            "prev_success": prev_success,
            "prev_fail": prev_fail,
            "attempt": attempt,
            "days_since_last": days_since,
            "bank": BANKS.index(random.choice(BANKS)),
            "success": success,
            "delay_bucket": delay_bucket,
        })
    return pd.DataFrame(rows)


def train_model(data_path: str = "training_data.csv") -> dict:
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
    else:
        df = _generate_synthetic_dataset(10000)
        df.to_csv(data_path, index=False)

    feature_cols = [
        "amount", "failure_code", "category", "hour", "day_of_month",
        "prev_success", "prev_fail", "attempt", "days_since_last", "bank",
    ]
    X = df[feature_cols]
    y_success = df["success"]
    y_delay = df["delay_bucket"]

    X_train, X_test, y_train, y_test = train_test_split(X, y_success, test_size=0.2, random_state=42)

    success_model = DecisionTreeClassifier(max_depth=8, random_state=42)
    success_model.fit(X_train, y_train)

    y_pred = success_model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    X_train_d, X_test_d, y_train_d, y_test_d = train_test_split(X, y_delay, test_size=0.2, random_state=42)
    delay_model = DecisionTreeClassifier(max_depth=8, random_state=42)
    delay_model.fit(X_train_d, y_train_d)

    model_dir = "models"
    os.makedirs(model_dir, exist_ok=True)
    with open(f"{model_dir}/success_model.pkl", "wb") as f:
        pickle.dump(success_model, f)
    with open(f"{model_dir}/delay_model.pkl", "wb") as f:
        pickle.dump(delay_model, f)

    feature_importance = dict(zip(feature_cols, success_model.feature_importances_))
    report = classification_report(y_test, y_pred, output_dict=True)

    result = {
        "accuracy": round(accuracy, 4),
        "feature_importance": {k: round(v, 4) for k, v in feature_importance.items()},
        "report": report,
        "train_size": len(X_train),
        "test_size": len(X_test),
    }
    with open(f"{model_dir}/metrics.json", "w") as f:
        json.dump(result, f, indent=2)

    print(f"Model trained. Accuracy: {accuracy:.4f}")
    print(f"Feature importance: {json.dumps(feature_importance, indent=2)}")
    return result


if __name__ == "__main__":
    train_model()
