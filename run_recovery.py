#!/usr/bin/env python3
import sys
import uuid
import logging
import hashlib
from datetime import datetime, timedelta
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from src.models.schemas import FailedPaymentEvent, DecisionAction
from src.compliance.guard import RBIComplianceGuard
from src.ai.predictor import heuristic_predict
from src.integration.razorpay import RazorpayStub
from src.integration.notify import MockWhatsAppAdapter
from src.ai.data_gen import generate_events
from src.models.database import (
    SessionLocal, PaymentEventRecord, ComplianceRecord,
    RetryRecord, NotificationRecord, SimulationResult,
)

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler("recovery.log"), logging.StreamHandler()],
)
logger = logging.getLogger("orchestrator")

console = Console()


class RecoveryError(Exception):
    pass


class IdempotencyKey:
    def __init__(self):
        self._seen = set()

    def generate(self, subscription_id: str, amount: int, failure_code: str) -> str:
        raw = f"{subscription_id}:{amount}:{failure_code}:{datetime.now().strftime('%Y%m%d%H')}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def check(self, key: str) -> bool:
        if key in self._seen:
            return False
        self._seen.add(key)
        return True


class RecoveryOrchestrator:
    def __init__(self, use_ml: bool = False):
        self.guard = RBIComplianceGuard()
        self.razorpay = RazorpayStub(test_mode=True)
        self.whatsapp = MockWhatsAppAdapter()
        self.history: dict = {}
        self.audit_log: list = []
        self.stats = defaultdict(int)
        self.use_ml = use_ml
        self.retry_timestamps: dict = defaultdict(list)
        self.db = SessionLocal()
        self.idempotency = IdempotencyKey()
        self.errors: list = []

    def _get_history(self, subscription_id: str) -> dict:
        return self.history.get(
            subscription_id,
            {"last_attempt": None, "retry_count_last_7d": 0, "mandate_revoked": False},
        )

    def _record_history(self, subscription_id: str, success: bool):
        if subscription_id not in self.history:
            self.history[subscription_id] = {
                "last_attempt": None,
                "retry_count_last_7d": 0,
                "mandate_revoked": False,
            }
        h = self.history[subscription_id]
        h["last_attempt"] = datetime.now()
        if not success:
            h["retry_count_last_7d"] += 1

    def _save_event(self, event: FailedPaymentEvent, event_id: str):
        record = PaymentEventRecord(
            id=event_id,
            subscription_id=event.subscription_id,
            customer_id=event.customer_id,
            amount=event.amount,
            currency=event.currency,
            failure_code=event.failure_code.value,
            merchant_category=event.merchant_category.value,
            timestamp=event.timestamp,
            attempt_count=event.attempt_count,
            bank=event.bank,
            previous_success_count=event.previous_success_count,
            previous_failure_count=event.previous_failure_count,
        )
        self.db.add(record)

    def _save_compliance(self, event_id: str, decision, sub_id: str):
        record = ComplianceRecord(
            id=str(uuid.uuid4()),
            event_id=event_id,
            subscription_id=sub_id,
            allowed=decision.allowed,
            action=decision.action.value,
            reason=decision.reason,
            requires_customer_action=decision.requires_customer_action,
            next_allowed_at=decision.next_allowed_at,
        )
        self.db.add(record)

    def _save_retry(self, event_id: str, event, ai_rec, action, outcome):
        record = RetryRecord(
            id=str(uuid.uuid4()),
            event_id=event_id,
            subscription_id=event.subscription_id,
            customer_id=event.customer_id,
            amount=event.amount,
            action_taken=action,
            ai_delay_hours=ai_rec["delay_hours"],
            ai_confidence=ai_rec["confidence"],
            outcome=outcome,
        )
        self.db.add(record)

    def process_event(self, event: FailedPaymentEvent) -> dict:
        self.stats["total_events"] += 1
        event_id = f"EVT_{uuid.uuid4().hex[:8]}"

        idem_key = self.idempotency.generate(
            event.subscription_id, event.amount, event.failure_code.value
        )
        if not self.idempotency.check(idem_key):
            self.stats["duplicates_skipped"] += 1
            return {"event_id": event_id, "outcome": "skipped_duplicate"}

        try:
            history = self._get_history(event.subscription_id)

            if self.use_ml:
                from src.ai.ml_predictor import ml_predict
                ai_rec = ml_predict(event)
            else:
                ai_rec = heuristic_predict(event)

            self.stats["ai_retries"] += 1 if ai_rec["recommended_action"] == "RETRY" else 0
            self.stats["ai_no_retry"] += 1 if ai_rec["recommended_action"] == "NO_RETRY" else 0

            decision = self.guard.check(
                event, history, self.retry_timestamps.get(event.subscription_id)
            )

            log_entry = {
                "event_id": event_id,
                "subscription_id": event.subscription_id,
                "customer_id": event.customer_id,
                "amount": event.amount,
                "failure_code": event.failure_code.value,
                "ai_action": ai_rec["recommended_action"],
                "ai_delay_hours": ai_rec["delay_hours"],
                "ai_confidence": ai_rec["confidence"],
                "compliance_allowed": decision.allowed,
                "compliance_action": decision.action.value,
                "compliance_reason": decision.reason,
                "outcome": "pending",
            }

            self._save_event(event, event_id)
            self._save_compliance(event_id, decision, event.subscription_id)

            if not decision.allowed:
                self.stats["compliance_blocks"] += 1
                if decision.action == DecisionAction.STEP_UP_LINK:
                    link = self.razorpay.create_payment_link(event.amount, event.customer_id)
                    self.whatsapp.send(
                        "stepup_link",
                        customer_id=event.customer_id,
                        amount=event.amount,
                        payment_url=link["url"],
                    )
                    log_entry["action"] = "STEP_UP_LINK_SENT"
                    log_entry["link_url"] = link["url"]
                    self.stats["step_up_links"] += 1
                elif decision.action == DecisionAction.STOP:
                    if "revoked" in decision.reason.lower():
                        self.stats["mandates_revoked"] += 1
                    else:
                        self.stats["mandates_exhausted"] += 1
                    log_entry["action"] = "STOPPED"
                log_entry["outcome"] = "blocked"
                self._record_history(event.subscription_id, False)
            else:
                retry_time = datetime.now() + timedelta(hours=ai_rec["delay_hours"])
                self.razorpay.charge_subscription(event.subscription_id, event.amount)
                self.whatsapp.send(
                    "retry_notification",
                    customer_id=event.customer_id,
                    amount=event.amount,
                    subscription_id=event.subscription_id,
                    retry_time=retry_time.strftime("%Y-%m-%d %H:%M"),
                )
                log_entry["action"] = "RETRY_SCHEDULED"
                log_entry["scheduled_time"] = retry_time.isoformat()
                log_entry["outcome"] = "scheduled"
                self._record_history(event.subscription_id, False)
                self.retry_timestamps[event.subscription_id].append(datetime.now())

            self._save_retry(event_id, event, ai_rec, log_entry.get("action", ""), log_entry["outcome"])
            self.audit_log.append(log_entry)
            return log_entry

        except Exception as e:
            self.stats["errors"] += 1
            self.errors.append({"event_id": event_id, "error": str(e)})
            logger.error("Error processing event %s: %s", event_id, e)
            fallback = {
                "event_id": event_id,
                "outcome": "error_fallback",
                "action": "STOP",
                "reason": f"Error: {str(e)}",
            }
            self.audit_log.append(fallback)
            return fallback

    def run(self, events=None, verbose=False, use_ml=False):
        self.use_ml = use_ml
        if events is None:
            events = generate_events(200)

        console.print(
            Panel.fit(
                "[bold cyan]MandateMind Recovery Engine[/]",
                box=box.DOUBLE,
            )
        )
        mode = "ML" if use_ml else "Heuristic"
        console.print(f"Mode: {mode} | Processing {len(events)} events...\n")

        for i, event in enumerate(events):
            result = self.process_event(event)
            if verbose and i < 5:
                self._print_event_result(event, result)

        self._save_simulation_result()
        try:
            self.db.commit()
        except Exception as e:
            logger.error("DB commit failed: %s", e)
        self._print_summary()
        return self.audit_log, dict(self.stats)

    def _print_event_result(self, event: FailedPaymentEvent, result: dict):
        if result.get("outcome") == "skipped_duplicate":
            console.print(f"  [yellow]#{result['event_id']}[/] DUPLICATE SKIPPED")
            return
        if result.get("outcome") == "error_fallback":
            console.print(f"  [red]#{result['event_id']}[/] ERROR: {result.get('reason', '')}")
            return
        color = "green" if result.get("compliance_allowed") else "red"
        console.print(
            f"  [{color}]#{result['event_id']}[/] {event.customer_id} | Rs.{event.amount} | "
            f"{event.failure_code.value} -> AI:{result.get('ai_action', 'N/A')} | "
            f"Compliance:{result.get('compliance_action', 'N/A')} | {result.get('outcome', 'N/A')}"
        )

    def _save_simulation_result(self):
        s = self.stats
        recovery_rate = 0
        if s["total_events"] > 0:
            auto_retries = s["ai_retries"] - s["compliance_blocks"]
            recovery_rate = round((auto_retries / s["total_events"]) * 100, 1)

        record = SimulationResult(
            id=str(uuid.uuid4()),
            total_events=s["total_events"],
            ai_retries=s["ai_retries"],
            ai_no_retry=s["ai_no_retry"],
            compliance_blocks=s["compliance_blocks"],
            retries_scheduled=s.get("ai_retries", 0) - s.get("compliance_blocks", 0),
            step_up_links=s.get("step_up_links", 0),
            mandates_exhausted=s.get("mandates_exhausted", 0),
            mandates_revoked=s.get("mandates_revoked", 0),
            recovery_rate=recovery_rate,
            run_mode="ml" if self.use_ml else "heuristic",
        )
        self.db.add(record)

    def _print_summary(self):
        table = Table(title="Recovery Summary", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")

        s = self.stats
        table.add_row("Total Events", str(s["total_events"]))
        table.add_row("AI -> Retry", str(s["ai_retries"]))
        table.add_row("AI -> No Retry", str(s["ai_no_retry"]))
        table.add_row("Compliance Blocks", str(s["compliance_blocks"]))

        auto_retries = s["ai_retries"] - s["compliance_blocks"]
        table.add_row("Retries Scheduled", str(auto_retries))
        table.add_row("Step-Up Links", str(s.get("step_up_links", 0)))
        table.add_row("Mandates Exhausted", str(s.get("mandates_exhausted", 0)))
        table.add_row("Mandates Revoked", str(s.get("mandates_revoked", 0)))
        table.add_row("Duplicates Skipped", str(s.get("duplicates_skipped", 0)))
        table.add_row("Errors", str(s.get("errors", 0)))

        recovery_rate = 0
        if s["total_events"] > 0:
            recovery_rate = round((auto_retries / s["total_events"]) * 100, 1)
        table.add_row("Recovery Rate", f"{recovery_rate}%")

        console.print()
        console.print(table)
        if self.errors:
            console.print(f"[yellow] {len(self.errors)} errors occurred (see recovery.log)[/]")
        console.print(f"[dim]Data saved to mandatemind.db | Audit log in recovery.log[/]")


def run_evaluation(events_count=10000):
    from src.ai.data_gen import generate_events as gen

    console.print(Panel.fit("[bold yellow]MandateMind Evaluation[/]", box=box.DOUBLE))

    events = gen(events_count)
    console.print(f"Generated {len(events)} events\n")

    configs = {
        "Heuristic": {"use_ml": False},
        "ML Model": {"use_ml": True},
    }

    results = {}
    for name, cfg in configs.items():
        console.print(f"\n[bold]Running: {name}[/]")
        orch = RecoveryOrchestrator(use_ml=cfg["use_ml"])
        _, stats = orch.run(events.copy(), verbose=False, use_ml=cfg["use_ml"])
        recovery_rate = 0
        if stats["total_events"] > 0:
            auto = stats["ai_retries"] - stats["compliance_blocks"]
            recovery_rate = round((auto / stats["total_events"]) * 100, 1)
        results[name] = {"recovery_rate": recovery_rate, "blocks": stats["compliance_blocks"]}

    table = Table(title="Evaluation Comparison", box=box.DOUBLE)
    table.add_column("System", style="cyan")
    table.add_column("Recovery %", style="green", justify="right")
    table.add_column("Blocks", style="red", justify="right")

    for name, r in results.items():
        table.add_row(name, f"{r['recovery_rate']}%", str(r["blocks"]))

    console.print()
    console.print(table)


def run_demo():
    console.print(Panel.fit("[bold yellow]MandateMind Demo: 3 Customer Scenarios[/]", box=box.DOUBLE))

    scenarios = [
        ("Customer A - Auto Recovery", FailedPaymentEvent(
            subscription_id="sub_CUST_A_001",
            customer_id="CUST_A",
            amount=2499,
            failure_code="INSUFFICIENT_FUNDS",
            merchant_category="SAAS",
            bank="HDFC",
            previous_success_count=12,
        )),
        ("Customer B - High Value Block", FailedPaymentEvent(
            subscription_id="sub_CUST_B_001",
            customer_id="CUST_B",
            amount=28000,
            failure_code="PAYMENT_FAILED",
            merchant_category="SAAS",
            bank="ICICI",
            previous_success_count=5,
        )),
        ("Customer C - Mandate Exhausted", FailedPaymentEvent(
            subscription_id="sub_CUST_C_001",
            customer_id="CUST_C",
            amount=8000,
            failure_code="NETWORK_ERROR",
            merchant_category="OTT_PLATFORM",
            bank="SBI",
            previous_success_count=2,
        )),
    ]

    orch = RecoveryOrchestrator(use_ml=False)

    for name, event in scenarios:
        console.print(f"\n[bold cyan]{'='*50}[/]")
        console.print(f"[bold]{name}[/]")
        console.print(f"Amount: Rs.{event.amount} | Failure: {event.failure_code.value} | Bank: {event.bank}")
        console.print(f"{'='*50}")

        for attempt in range(1, 4):
            result = orch.process_event(event)
            if result.get("outcome") == "error_fallback":
                console.print(f"  [red]Attempt {attempt}: ERROR - {result.get('reason', '')}[/]")
                break
            if result.get("outcome") == "skipped_duplicate":
                console.print(f"  [yellow]Attempt {attempt}: DUPLICATE SKIPPED[/]")
                continue

            color = "green" if result.get("compliance_allowed") else "red"
            console.print(
                f"  [bold]Attempt {attempt}:[/] [{color}]{result.get('compliance_action', 'N/A')}[/]"
                f" - {result.get('compliance_reason', '')}"
            )

            if not result.get("compliance_allowed"):
                if result.get("compliance_action") == "STEP_UP_LINK":
                    console.print(f"  [cyan]  -> Payment link sent: {result.get('link_url', 'N/A')}[/]")
                elif result.get("compliance_action") == "STOP":
                    console.print(f"  [red]  -> Mandate halted, no more retries[/]")
                break

    try:
        orch.db.commit()
    except Exception:
        pass

    console.print(f"\n[bold green]Demo complete. Data saved to mandatemind.db[/]")


if __name__ == "__main__":
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    ml_mode = "--ml" in sys.argv
    eval_mode = "--eval" in sys.argv
    demo_mode = "--demo" in sys.argv
    count = 200

    for arg in sys.argv:
        if arg.startswith("--count="):
            count = int(arg.split("=")[1])

    if demo_mode:
        run_demo()
    elif eval_mode:
        run_evaluation(count)
    else:
        orchestrator = RecoveryOrchestrator(use_ml=ml_mode)
        orchestrator.run(verbose=verbose, use_ml=ml_mode)
