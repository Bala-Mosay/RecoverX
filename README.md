# MandateMind / PayShield AI

AI-powered payment recovery engine for recurring payments that enforces RBI e-mandate regulations.

## Features

- AI-powered retry timing (heuristic + ML model)
- RBI compliance guard (24h notice, 15k/1L AFA thresholds, 3-retry limit)
- Idempotent event processing (no duplicate retries)
- SQLite audit trail (events, decisions, retries)
- Demo script with 3 customer scenarios
- Docker support

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run demo (3 scenarios)
python demo.py

# Run simulation (200 events, heuristic)
python run_recovery.py

# Run with ML model
python run_recovery.py --ml

# Run evaluation comparison
python run_recovery.py --eval --count=2000

# Run tests
python -m pytest tests/ -v

# View dashboard
python src/dashboard/dashboard.py
```

## Docker

```bash
# Build and run
docker-compose up

# Run tests in container
docker-compose run tests
```

## Commands

| Command | Description |
|---------|-------------|
| `python demo.py` | Run 3 customer demo scenarios |
| `python run_recovery.py` | Heuristic mode (200 events) |
| `python run_recovery.py --ml` | ML model mode |
| `python run_recovery.py --eval` | Compare heuristic vs ML |
| `python run_recovery.py -v` | Verbose output |
| `python -m pytest tests/ -v` | Run 27 tests |
| `python -m src.ai.train_model` | Retrain ML model |
| `docker-compose up` | Run in Docker |

## Project Structure

```
src/
  models/
    schemas.py          # Pydantic data models
    database.py         # SQLAlchemy DB (SQLite)
  compliance/
    guard.py            # RBIComplianceGuard
  ai/
    predictor.py        # Heuristic predictor
    ml_predictor.py     # ML predictor (scikit-learn)
    train_model.py      # ML training
    data_gen.py         # Synthetic data generator
  integration/
    razorpay.py         # Razorpay API stubs
    notify.py           # Mock WhatsApp adapter
  dashboard/
    dashboard.py        # Dashboard (Streamlit/console)
tests/                  # 27 tests
models/                 # Trained ML models
run_recovery.py         # Main orchestrator
demo.py                 # Demo script
Dockerfile              # Docker build
docker-compose.yml      # Docker compose
```

## How it works

```
Failed Payment Event
    |
    v
Idempotency Check --> Skip if duplicate
    |
    v
AI Predictor --> "Retry in Xh" / "Don't retry"
    |
    v
ComplianceGuard --> ALLOWED / BLOCKED
    |
    v
Schedule Retry / Send Step-Up Link / Stop
    |
    v
SQLite DB (audit trail)
```

## License

Internal project for Razorpay AI Buildathon 2026.
