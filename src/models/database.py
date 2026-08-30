from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, Enum as SAEnum
from datetime import datetime

DATABASE_URL = "sqlite:///mandatemind.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class PaymentEventRecord(Base):
    __tablename__ = "payment_events"

    id = Column(String, primary_key=True)
    subscription_id = Column(String, index=True)
    customer_id = Column(String, index=True)
    amount = Column(Integer)
    currency = Column(String, default="INR")
    failure_code = Column(String)
    merchant_category = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    attempt_count = Column(Integer, default=1)
    bank = Column(String, default="")
    previous_success_count = Column(Integer, default=0)
    previous_failure_count = Column(Integer, default=0)


class ComplianceRecord(Base):
    __tablename__ = "compliance_decisions"

    id = Column(String, primary_key=True)
    event_id = Column(String, index=True)
    subscription_id = Column(String, index=True)
    allowed = Column(Boolean)
    action = Column(String)
    reason = Column(Text)
    requires_customer_action = Column(Boolean, default=False)
    next_allowed_at = Column(DateTime, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)


class RetryRecord(Base):
    __tablename__ = "retry_actions"

    id = Column(String, primary_key=True)
    event_id = Column(String, index=True)
    subscription_id = Column(String, index=True)
    customer_id = Column(String, index=True)
    amount = Column(Integer)
    action_taken = Column(String)
    ai_delay_hours = Column(Float)
    ai_confidence = Column(Float)
    scheduled_time = Column(DateTime, nullable=True)
    outcome = Column(String, default="pending")
    timestamp = Column(DateTime, default=datetime.now)


class NotificationRecord(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True)
    event_id = Column(String, index=True)
    channel = Column(String)
    template = Column(String)
    recipient = Column(String)
    payload = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id = Column(String, primary_key=True)
    total_events = Column(Integer)
    ai_retries = Column(Integer)
    ai_no_retry = Column(Integer)
    compliance_blocks = Column(Integer)
    retries_scheduled = Column(Integer)
    step_up_links = Column(Integer)
    mandates_exhausted = Column(Integer)
    mandates_revoked = Column(Integer)
    recovery_rate = Column(Float)
    run_mode = Column(String)
    timestamp = Column(DateTime, default=datetime.now)


Base.metadata.create_all(bind=engine)
