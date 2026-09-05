# RecoverX Demo Guide

## Quick Start (5 minutes)

Run this single command to see the full demo:

```bash
python demo.py
```

---

## Full Demo Walkthrough

### Step 1: Run Core Recovery Engine

```bash
# Run with 200 simulated events (heuristic mode)
python run_recovery.py

# Run with ML model
python run_recovery.py --ml

# Run comparison (heuristic vs ML)
python run_recovery.py --eval
```

### Step 2: Generate WhatsApp Notifications

```bash
# Generate 10 sample WhatsApp notifications
python run_whatsapp_sim.py -n 10
```

### Step 3: Start the Dashboard

```bash
# Open browser to http://localhost:8501
streamlit run src/dashboard/streamlit_app.py
```

Dashboard tabs:
- **Overview** - Total events, compliance decisions, recovery rate
- **Events** - All payment failure events with filters
- **Compliance** - Allowed vs blocked decisions
- **Notifications** - WhatsApp message previews
- **Simulations** - Historical run results

### Step 4: Start the API Server (Optional)

```bash
# Start webhook receiver
python -m uvicorn src.api.main:app --reload

# Test health endpoint
curl http://localhost:8000/health

# Test metrics endpoint
curl http://localhost:8000/metrics

# Test notifications endpoint
curl http://localhost:8000/notifications
```

---

## Demo Script Explained

### 3 Customer Scenarios

| Customer | Amount | Failure | Expected Outcome |
|----------|--------|---------|------------------|
| CUST_A | Rs.2,499 | INSUFFICIENT_FUNDS | Auto retry (below 15k) |
| CUST_B | Rs.28,000 | PAYMENT_FAILED | Block + step-up link (>15k) |
| CUST_C | Rs.8,000 | NETWORK_ERROR | 3 retries then halt |

### What Happens in Each Scenario

**CUST_A (Rs.2,499 - INSUFFICIENT_FUNDS)**
- AI predicts: Retry in 6 hours (salary may credit)
- Compliance: Allowed (below Rs.15,000 threshold)
- Action: Schedule retry + send WhatsApp notification

**CUST_B (Rs.28,000 - PAYMENT_FAILED)**
- AI predicts: Retry in 4 hours
- Compliance: BLOCKED (above Rs.15,000 threshold)
- Action: Send step-up link for AFA verification

**CUST_C (Rs.8,000 - NETWORK_ERROR)**
- Attempt 1: AI recommends retry in 1h, compliance allows
- Attempt 2: AI recommends retry in 1h, compliance allows
- Attempt 3: AI recommends retry in 1h, compliance BLOCKS (max 3 retries/7 days)
- Action: Mandate exhausted, notify customer

---

## Commands Summary

| Command | Description |
|---------|-------------|
| `python demo.py` | Run 3 customer demo |
| `python run_recovery.py` | Run 200 events (heuristic) |
| `python run_recovery.py --ml` | Run with ML model |
| `python run_recovery.py --eval` | Compare heuristic vs ML |
| `python run_whatsapp_sim.py -n 10` | Generate WhatsApp notifications |
| `streamlit run src/dashboard/streamlit_app.py` | Start dashboard |
| `python -m uvicorn src.api.main:app --reload` | Start API server |
| `python -m pytest tests/ -v` | Run all 35 tests |

---

## For Hackathon Presentation

### Recommended Flow

1. `python demo.py` - Show core engine working
2. `python run_whatsapp_sim.py -n 5` - Show WhatsApp notifications
3. `streamlit run src/dashboard/streamlit_app.py` - Show dashboard
4. Show the 3 customer scenarios with expected vs actual outcomes
5. Highlight RBI compliance rules being enforced

### Key Points to Highlight

- **RBI Compliance**: 24h pre-debit notice, Rs.15k/1L thresholds, 3-retry limit
- **AI Decision Making**: Heuristic rules + ML model (68.7% accuracy)
- **Real Razorpay Integration**: Test mode with real API calls
- **WhatsApp Notifications**: Pre-debit, retry, step-up link, mandate exhausted
- **Audit Trail**: All events, decisions, and notifications stored in SQLite
- **Docker Ready**: Full containerization with docker-compose
