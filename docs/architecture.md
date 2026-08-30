# Architecture

## System Overview

MandateMind (PayShield AI) is an AI-powered payment recovery engine that processes failed recurring payments through a compliance-first pipeline, ensuring RBI e-mandate regulations are never violated.

## Data Flow

```
Razorpay Payment Failure
        |
        v
+------------------+
| Webhook Receiver |  <-- FastAPI endpoint
| (POST /webhook)  |
+------------------+
        |
        v
+------------------+
|  AI Predictor    |  <-- Heuristic rules / ML model
|  (delay_hours)   |
+------------------+
        |
        v
+------------------+
| Compliance Guard |  <-- RBI rules enforcement
| (3 rules)        |
+------------------+
        |
        v
+------------------+
| Action Executor  |  <-- Retry / Step-up Link / Stop
+------------------+
        |
        v
+------------------+
|   SQLite DB      |  <-- Audit trail
+------------------+
        |
        v
+------------------+
|   Dashboard      |  <-- Streamlit / Console
+------------------+
```

## Components

### 1. Webhook Receiver (`src/api/`)

- **FastAPI** server receives Razorpay webhooks
- Verifies HMAC signature
- Parses event type and routes to handler
- Maps Razorpay error codes to internal codes

### 2. AI Predictor (`src/ai/`)

Two modes:

| Mode | Accuracy | Speed | Use Case |
|------|----------|-------|----------|
| Heuristic | Rule-based | Instant | Default |
| ML (DecisionTree) | 68.7% | ~1ms | When trained model available |

The AI recommends:
- `RETRY` with delay (hours)
- `NO_RETRY` (card expired, auth failed, mandate not found)

### 3. Compliance Guard (`src/compliance/`)

Enforces 3 RBI rules:

| Rule | Description |
|------|-------------|
| **24h Pre-Debit** | Cannot debit without 24h advance notice |
| **AFA Threshold** | Rs.15,000 standard / Rs.1,00,000 for Insurance, SIP, CC bills |
| **Retry Limit** | Max 3 retries per 7-day window |

Output: `ComplianceDecision` with action:
- `SCHEDULE_RETRY` - Allowed, schedule retry
- `STEP_UP_LINK` - Requires AFA, send step-up link
- `STOP` - Blocked, do not retry

### 4. Integration (`src/integration/`)

- **Razorpay SDK** - Real API calls for payment links (test mode)
- **Mock WhatsApp** - Console output for notifications

### 5. Database (`src/models/database.py`)

SQLite with SQLAlchemy ORM.

### 6. Dashboard

- **Streamlit** (`src/dashboard/streamlit_app.py`) - Web UI with 4 tabs
- **Console** (`src/dashboard/dashboard.py`) - Rich terminal output

## Database Schema

### payment_events

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT (PK) | Event ID |
| subscription_id | TEXT | Razorpay subscription ID |
| customer_id | TEXT | Customer identifier |
| amount | INTEGER | Amount in paise |
| currency | TEXT | Default: INR |
| failure_code | TEXT | Mapped error code |
| merchant_category | TEXT | Business category |
| timestamp | DATETIME | Event time |
| attempt_count | INTEGER | Retry attempt number |
| bank | TEXT | Bank identifier |
| previous_success_count | INTEGER | Historical successes |
| previous_failure_count | INTEGER | Historical failures |

### compliance_decisions

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT (PK) | Decision ID |
| event_id | TEXT (FK) | Links to payment_events |
| subscription_id | TEXT | Razorpay subscription ID |
| allowed | BOOLEAN | Retry allowed? |
| action | TEXT | SCHEDULE_RETRY / STEP_UP_LINK / STOP |
| reason | TEXT | Human-readable reason |
| requires_customer_action | BOOLEAN | Needs customer intervention? |
| next_allowed_at | DATETIME | When retry becomes allowed |
| timestamp | DATETIME | Decision time |

### retry_actions

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT (PK) | Retry ID |
| event_id | TEXT (FK) | Links to payment_events |
| subscription_id | TEXT | Razorpay subscription ID |
| customer_id | TEXT | Customer identifier |
| amount | INTEGER | Amount in paise |
| action_taken | TEXT | RETRY / STEP_UP_LINK_SENT / STOPPED |
| ai_delay_hours | FLOAT | AI recommended delay |
| ai_confidence | FLOAT | AI confidence score |
| scheduled_time | DATETIME | When retry is scheduled |
| outcome | TEXT | pending / success / failed |
| timestamp | DATETIME | Action time |

### simulation_results

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT (PK) | Result ID |
| total_events | INTEGER | Total events simulated |
| ai_retries | INTEGER | Events with retry |
| ai_no_retry | INTEGER | Events without retry |
| compliance_blocks | INTEGER | Blocked by compliance |
| retries_scheduled | INTEGER | Retries scheduled |
| step_up_links | INTEGER | Step-up links sent |
| mandates_exhausted | INTEGER | Retries exhausted |
| mandates_revoked | INTEGER | Mandates revoked |
| recovery_rate | FLOAT | Success percentage |
| run_mode | TEXT | heuristic / ml / eval |
| timestamp | DATETIME | Run time |

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| RAZORPAY_TEST_KEY | Razorpay test API key | Yes |
| RAZORPAY_TEST_SECRET | Razorpay test API secret | Yes |
| RAZORPAY_WEBHOOK_SECRET | Webhook signature verification | Optional |

## Tech Stack

| Component | Technology |
|-----------|------------|
| API Framework | FastAPI |
| ORM | SQLAlchemy |
| Database | SQLite |
| ML Model | scikit-learn DecisionTree |
| Dashboard | Streamlit |
| Integration | Razorpay SDK |
| Testing | pytest |
| Containerization | Docker |
| CI/CD | GitHub Actions |
