# MandateMind / PayShield AI

AI-powered payment recovery engine for recurring payments that enforces RBI e-mandate regulations.

## Features

- AI-powered retry timing (heuristic + ML model)
- RBI compliance guard (24h notice, 15k/1L AFA thresholds, 3-retry limit)
- Razorpay SDK integration (real API calls)
- FastAPI webhook receiver
- SQLite audit trail
- Streamlit dashboard
- Docker support
- GitHub Actions CI/CD

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run demo
python demo.py

# Run simulation
python run_recovery.py

# Run with ML model
python run_recovery.py --ml

# Start API server
python -m uvicorn src.api.main:app --reload

# Start dashboard
streamlit run src/dashboard/streamlit_app.py

# Run tests
python -m pytest tests/ -v
```

## Docker

```bash
# Run all services
docker-compose up

# Run specific service
docker-compose up api
docker-compose up dashboard
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/webhook/razorpay` | POST | Razorpay webhook receiver |
| `/metrics` | GET | Recovery metrics |

## Webhook Setup (ngrok)

```bash
# Install ngrok
npm install -g ngrok

# Start API server
python -m uvicorn src.api.main:app --port 8000

# Expose to internet
ngrok http 8000

# Set webhook URL in Razorpay Dashboard
# https://xxxx.ngrok-free.app/webhook/razorpay
```

## Dashboard

```bash
# Start Streamlit dashboard
streamlit run src/dashboard/streamlit_app.py

# Open http://localhost:8501
```

## Commands

| Command | Description |
|---------|-------------|
| `python demo.py` | Run 3 demo scenarios |
| `python run_recovery.py` | Heuristic mode |
| `python run_recovery.py --ml` | ML model mode |
| `python run_recovery.py --eval` | Compare heuristic vs ML |
| `python -m pytest tests/ -v` | Run 27 tests |
| `python -m uvicorn src.api.main:app` | Start API server |
| `streamlit run src/dashboard/streamlit_app.py` | Start dashboard |

## Project Structure

```
src/
  api/
    main.py             # FastAPI app
    webhook.py          # Razorpay webhook handler
    models.py           # Webhook models
  models/
    schemas.py          # Pydantic data models
    database.py         # SQLAlchemy DB
  compliance/
    guard.py            # RBIComplianceGuard
  ai/
    predictor.py        # Heuristic predictor
    ml_predictor.py     # ML predictor
    train_model.py      # ML training
    data_gen.py         # Data generator
  integration/
    razorpay.py         # Razorpay SDK
    notify.py           # Mock WhatsApp
  dashboard/
    streamlit_app.py    # Streamlit dashboard
    dashboard.py        # Console dashboard
tests/                  # 27 tests
.github/workflows/      # CI/CD
```

## License

Internal project for Razorpay AI Buildathon 2026.
