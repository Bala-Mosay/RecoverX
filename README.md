# RecoverX

> AI-Powered Payment Recovery Engine with RBI e-Mandate Compliance

Built for Razorpay AI Buildathon 2026.

---

## The Problem

Recurring payments (subscriptions, SIPs, insurance premiums) fail frequently due to insufficient funds, network errors, or bank declines. Merchants lose revenue when customers don't retry. But RBI's 2024 e-mandate framework imposes strict rules:

- **24-hour pre-debit notice** before every retry
- **Rs.15,000 AFA threshold** (Rs.1,00,000 for Insurance, SIP, Credit Card bills)
- **Max 3 retries** per 7-day window
- **Customer can cancel** mandates anytime

Manual compliance is error-prone. Most merchants either over-retry (violating RBI rules) or under-retry (losing revenue).

## The Solution

RecoverX is an AI engine that sits between Razorpay and the merchant, automatically deciding:

1. **When to retry** - AI predicts optimal delay based on failure type and history
2. **Whether to retry** - Compliance guard enforces all RBI rules
3. **What action to take** - Retry, send step-up link, or stop entirely

---

## How It Works

### Data Flow

```
Razorpay Payment Failure
        |
        v
+------------------+
| Webhook Receiver |  <-- FastAPI receives Razorpay events
+------------------+
        |
        v
+------------------+
|   AI Predictor   |  <-- Recommends delay (hours) and confidence
+------------------+
        |
        v
+------------------+
| Compliance Guard |  <-- Checks 3 RBI rules, allows/blocks
+------------------+
        |
        v
+------------------+
| Action Executor  |  <-- Retry / Step-up Link / Stop
+------------------+
        |
        v
+------------------+
|  WhatsApp Notify |  <-- Pre-debit notice, retry alert, step-up link
+------------------+
        |
        v
+------------------+
|   SQLite DB      |  <-- Full audit trail
+------------------+
```

### AI Decision Engine

The AI uses two modes:

| Mode | How it Works | Accuracy |
|------|-------------|----------|
| **Heuristic** | Rule-based: maps failure codes to optimal delays | Baseline |
| **ML Model** | DecisionTree trained on 10k synthetic events | 68.7% |

**Example decisions:**

| Failure Code | AI Recommendation | Reason |
|-------------|-------------------|--------|
| INSUFFICIENT_FUNDS | Retry in 6 hours | Salary may credit by evening |
| NETWORK_ERROR | Retry in 1 hour | Quick retry likely to succeed |
| CARD_EXPIRED | No retry | Requires customer action |
| AUTHENTICATION_FAILED | No retry | 3DS/OTP failure needs customer |

### RBI Compliance Rules

```
Rule 1: 24-Hour Pre-Debit Notice
  - Cannot debit without notifying customer 24h in advance
  - Tracks last_attempt timestamp per subscription

Rule 2: AFA Threshold
  - Standard: Rs.15,000
  - Enhanced: Rs.1,00,000 (Insurance, Mutual Fund SIP, Credit Card Bill)
  - Above threshold: send step-up authentication link

Rule 3: Retry Limit
  - Max 3 retries per 7-day rolling window
  - After 3 retries: halt subscription, notify customer
```

---

## 3 Demo Scenarios

### Scenario 1: Auto-Recovery (CUST_A)
```
Amount:    Rs.2,499
Failure:   INSUFFICIENT_FUNDS
Category:  SAAS
Result:    ALLOWED -> Retry scheduled in 6 hours
```
AI detects insufficient funds, recommends evening retry when salary may credit. Compliance allows (below Rs.15,000 threshold).

### Scenario 2: High-Value Block (CUST_B)
```
Amount:    Rs.28,000
Failure:   PAYMENT_FAILED
Category:  SAAS
Result:    BLOCKED -> Step-up link sent
```
Amount exceeds Rs.15,000 threshold. Compliance blocks automatic retry and sends AFA verification link to customer.

### Scenario 3: Mandate Exhausted (CUST_C)
```
Amount:    Rs.8,000
Failure:   NETWORK_ERROR
Category:  OTT Platform
Attempt 1: ALLOWED -> Retry in 1 hour
Attempt 2: ALLOWED -> Retry in 1 hour
Attempt 3: BLOCKED -> Max retries reached
```
3 retries exhausted within 7-day window. System halts and notifies customer to update payment method.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run 3-customer demo
python demo.py

# Run 200-event simulation
python run_recovery.py

# Compare Heuristic vs ML
python run_recovery.py --eval

# Generate WhatsApp notifications
python run_whatsapp_sim.py -n 10

# Start dashboard (opens browser)
streamlit run src/dashboard/streamlit_app.py

# Start API server
python -m uvicorn src.api.main:app --reload

# Run all 35 tests
python -m pytest tests/ -v
```

---

## Dashboard

Premium dark theme built with Streamlit. Start with: `streamlit run src/dashboard/streamlit_app.py`

| Tab | Shows |
|-----|-------|
| **Overview** | 2+2 metric card grid, recovery rate ring, compliance bar chart, retry pie chart, amount histogram |
| **Events** | Filterable payment event table with failure code and amount range filters |
| **Compliance** | Allowed vs blocked bar chart, top blocking reasons, decision history |
| **Notifications** | WhatsApp phone mockup with message previews, template distribution chart, filterable history |
| **Simulations** | Historical run results table, recovery rate time-series |

**Design:** Outfit font, `#0c1310` background, emerald `#5ee0a8` accent, grain texture overlay, double-bezel card architecture, spring transitions, inline SVG icons, Plotly charts.

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/webhook/razorpay` | POST | Razorpay webhook receiver |
| `/metrics` | GET | Recovery metrics |
| `/notifications` | GET | WhatsApp notification history |

### Example: Send a test webhook

```bash
curl -X POST http://localhost:8000/webhook/razorpay \
  -H "Content-Type: application/json" \
  -d '{
    "event": "subscription.charged_failed",
    "payload": {
      "subscription": {"payload": {"id": "sub_test", "status": "active", "customer_id": "cust_001"}},
      "payment": {"payload": {"id": "pay_test", "status": "failed", "amount": 249900, "error_code": "INSUFFICIENT_FUNDS"}}
    }
  }'
```

---

## Webhook Setup (ngrok)

```bash
# Start API server
python -m uvicorn src.api.main:app --port 8000

# Expose to internet
ngrok http 8000

# Copy the URL (e.g., https://xxxx.ngrok-free.app)
# Set it in Razorpay Dashboard -> Webhooks -> https://xxxx.ngrok-free.app/webhook/razorpay
```

---

## WhatsApp Notifications

The system sends 4 types of WhatsApp messages:

| Template | When | Content |
|----------|------|---------|
| `pre_debit_notice` | 24h before debit | "A payment of Rs.X will be debited..." |
| `retry_notification` | Retry scheduled | "We will retry your payment at..." |
| `stepup_link` | AFA required | "Complete payment here: [link]" |
| `mandate_exhausted` | Max retries hit | "Your subscription has been paused..." |

Generate sample notifications: `python run_whatsapp_sim.py -n 10`

---

## Evaluation Results

```
python run_recovery.py --eval

+-----------+------------+--------+
| System    | Recovery % | Blocks |
|-----------+------------+--------|
| Heuristic |      43.5% |     99 |
| ML Model  |      26.5% |     99 |
+-----------+------------+--------+
```

- **Heuristic** recovers 43.5% of failed payments
- **ML Model** is more conservative (26.5%) but may be more accurate
- **Compliance blocks** are identical (99) - same RBI rules enforced

### ML Model Details

| Property | Value |
|----------|-------|
| Model | DecisionTreeClassifier (max_depth=8) |
| Training data | 10,000 synthetic events (8,000 train / 2,000 test) |
| Accuracy | 68.7% |
| Precision (retry) | 50.9% |
| Recall (retry) | 37.1% |
| Precision (no-retry) | 74.1% |
| Recall (no-retry) | 83.4% |

**Feature importance:**

| Feature | Importance |
|---------|-----------|
| failure_code | 40.3% |
| amount | 18.3% |
| attempt_count | 8.7% |
| previous_success_count | 7.5% |
| days_since_last | 5.4% |
| hour_of_day | 5.3% |
| day_of_month | 5.0% |
| previous_failure_count | 3.5% |
| bank | 3.5% |
| merchant_category | 2.6% |

---

## Tech Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.13.7 |
| API | FastAPI + Uvicorn | 0.110+ |
| Database | SQLite + SQLAlchemy ORM | 2.0+ |
| ML | scikit-learn DecisionTree | 1.4+ |
| Dashboard | Streamlit + Plotly | 1.62+ |
| Integration | Razorpay SDK | 1.4+ |
| CLI Output | Rich (tables, panels) | 13+ |
| Data Gen | Faker | 24+ |
| Testing | pytest | 8.0+ |
| Container | Docker + docker-compose | - |
| CI/CD | GitHub Actions | - |
| Frontend Font | Outfit (Google Fonts) | 400-700 |

---

## Project Structure

```
RecoverX/
  demo.py                          # 3-customer demo
  run_recovery.py                  # Main orchestrator
  run_whatsapp_sim.py              # WhatsApp notification simulator
  requirements.txt                 # Dependencies
  .env                             # Razorpay API keys (gitignored)
  
  src/
    api/
      main.py                      # FastAPI webhook receiver
      webhook.py                   # Signature verification
      models.py                    # Webhook payload models
    models/
      schemas.py                   # Pydantic data models
      database.py                  # SQLAlchemy DB models
    compliance/
      guard.py                     # RBIComplianceGuard (3 rules)
    ai/
      predictor.py                 # Heuristic predictor
      ml_predictor.py              # ML predictor
      train_model.py               # Model training
      data_gen.py                  # Synthetic data generator
    integration/
      razorpay.py                  # Razorpay SDK client
      notify.py                    # Mock WhatsApp adapter
    dashboard/
      streamlit_app.py             # Streamlit web dashboard
      dashboard.py                 # Console dashboard
  
  tests/                           # 35 tests
    test_compliance.py             # 10 compliance tests
    test_ai.py                     # 7 AI predictor tests
    test_edge_cases.py             # 10 edge case tests
    test_integration.py            # 8 API endpoint tests
  
  docs/
    architecture.md                # System architecture
    api_contracts.md               # API documentation
  
  models/
    success_model.pkl              # Trained ML model (success prediction)
    delay_model.pkl                # Trained ML model (delay prediction)
    metrics.json                   # Model accuracy and feature importance
  
  .github/workflows/ci.yml        # CI/CD pipeline
  Dockerfile                       # Docker build
  docker-compose.yml               # Docker compose
```

---

## License

Internal project for Razorpay AI Buildathon 2026.
