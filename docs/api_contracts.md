# API Contracts

## Base URL

```
http://localhost:8000
```

## Endpoints

### Health Check

```
GET /health
```

**Response (200):**
```json
{
  "status": "healthy",
  "timestamp": "2026-08-30T14:30:00.000Z",
  "service": "MandateMind"
}
```

---

### Webhook Receiver

```
POST /webhook/razorpay
```

**Headers:**
```
Content-Type: application/json
X-Razorpay-Signature: <hmac-sha256-signature>
```

**Request Body (Payment Failed):**
```json
{
  "event": "subscription.charged_failed",
  "payload": {
    "subscription": {
      "payload": {
        "id": "sub_abc123",
        "status": "active",
        "customer_id": "cust_xyz789"
      }
    },
    "payment": {
      "payload": {
        "id": "pay_123456",
        "status": "failed",
        "amount": 249900,
        "currency": "INR",
        "error_code": "INSUFFICIENT_FUNDS",
        "error_description": "Insufficient funds"
      }
    }
  }
}
```

**Response (200):**
```json
{
  "status": "processed",
  "event_type": "payment_failure",
  "subscription_id": "sub_abc123",
  "compliance_allowed": true,
  "action": "SCHEDULE_RETRY",
  "reason": "All compliance checks passed"
}
```

**Response (200) - Blocked:**
```json
{
  "status": "processed",
  "event_type": "payment_failure",
  "subscription_id": "sub_abc123",
  "compliance_allowed": false,
  "action": "STEP_UP_LINK",
  "reason": "Amount 28000 exceeds threshold 15000 for category SAAS"
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Invalid JSON payload |
| 401 | Invalid webhook signature |

---

### Metrics

```
GET /metrics
```

**Response (200):**
```json
{
  "total_events": 150,
  "total_compliance_decisions": 150,
  "allowed": 90,
  "blocked": 60,
  "recovery_rate": 60.0
}
```

---

## Event Types

| Event | Description |
|-------|-------------|
| `subscription.pending` | Payment attempt pending |
| `subscription.charged_failed` | Payment failed |
| `subscription.charged` | Payment succeeded |
| `subscription.halted` | Subscription halted |
| `subscription.cancelled` | Subscription cancelled |

## Failure Codes

| Code | Description | AI Action | Delay (hours) |
|------|-------------|-----------|---------------|
| INSUFFICIENT_FUNDS | Not enough balance | RETRY | 6 |
| NETWORK_ERROR | Bank connection issue | RETRY | 1 |
| TECHNICAL_ERROR | Bank server error | RETRY | 2 |
| PAYMENT_FAILED | Generic failure | RETRY | 4 |
| CARD_EXPIRED | Card expired | NO_RETRY | 0 |
| AUTHENTICATION_FAILED | 3DS/auth failure | NO_RETRY | 0 |
| BANK_DECLINED | Bank rejected | RETRY | 8 |
| LIMIT_EXCEEDED | Daily limit hit | RETRY | 12 |
| MANDATE_NOT_FOUND | E-mandate missing | NO_RETRY | 0 |
| UNKNOWN | Unclassified error | RETRY | 4 |

## Compliance Actions

| Action | Description |
|--------|-------------|
| SCHEDULE_RETRY | Retry allowed, schedule for later |
| STEP_UP_LINK | Requires AFA, send step-up link |
| STOP | Block, do not retry |

## Compliance Rules

| Rule | Threshold |
|------|-----------|
| 24h Pre-Debit | Must notify 24h before debit |
| Standard AFA | Rs.15,000 |
| Enhanced AFA (Insurance, SIP, CC) | Rs.1,00,000 |
| Max Retries | 3 per 7-day window |

## Database Tables

### payment_events
- `id` (TEXT, PK)
- `subscription_id` (TEXT)
- `customer_id` (TEXT)
- `amount` (INTEGER, paise)
- `failure_code` (TEXT)
- `merchant_category` (TEXT)
- `timestamp` (DATETIME)

### compliance_decisions
- `id` (TEXT, PK)
- `event_id` (TEXT, FK)
- `allowed` (BOOLEAN)
- `action` (TEXT)
- `reason` (TEXT)
- `requires_customer_action` (BOOLEAN)
- `next_allowed_at` (DATETIME)
- `timestamp` (DATETIME)

### retry_actions
- `id` (TEXT, PK)
- `event_id` (TEXT, FK)
- `action_taken` (TEXT)
- `ai_delay_hours` (FLOAT)
- `ai_confidence` (FLOAT)
- `outcome` (TEXT)
- `timestamp` (DATETIME)
