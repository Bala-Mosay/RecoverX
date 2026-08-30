#!/usr/bin/env python3
"""
MandateMind Demo Script
Runs 3 customer scenarios to showcase the recovery engine.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from run_recovery import RecoveryOrchestrator
from src.models.schemas import FailedPaymentEvent

console = Console()


def print_header():
    console.print(Panel.fit(
        "[bold cyan]MandateMind / PayShield AI[/]\n"
        "[dim]AI-Powered Payment Recovery Engine with RBI Compliance[/]",
        box=box.DOUBLE,
    ))


def print_scenarios():
    console.print("\n[bold]3 Demo Customer Scenarios:[/]\n")

    table = Table(box=box.ROUNDED)
    table.add_column("Customer", style="cyan", width=12)
    table.add_column("Amount", style="green", width=10)
    table.add_column("Failure", width=18)
    table.add_column("Category", width=12)
    table.add_column("Expected Outcome", width=30)

    table.add_row("CUST_A", "Rs.2,499", "INSUFFICIENT_FUNDS", "SAAS", "Auto retry (below 15k)")
    table.add_row("CUST_B", "Rs.28,000", "PAYMENT_FAILED", "SAAS", "Block + step-up link (>15k)")
    table.add_row("CUST_C", "Rs.8,000", "NETWORK_ERROR", "OTT", "3 retries then halt")

    console.print(table)


def run_scenario(name: str, event: FailedPaymentEvent, orch: RecoveryOrchestrator):
    console.print(f"\n[bold cyan]{'='*60}[/]")
    console.print(f"[bold]{name}[/]")
    console.print(f"Amount: Rs.{event.amount} | Failure: {event.failure_code.value} | Bank: {event.bank}")
    console.print(f"History: {event.previous_success_count} successful, {event.previous_failure_count} failed")
    console.print(f"{'='*60}\n")

    for attempt in range(1, 4):
        console.print(f"[bold]Attempt {attempt}:[/]", end=" ")
        result = orch.process_event(event)

        if result.get("outcome") == "error_fallback":
            console.print(f"[red]ERROR - {result.get('reason', '')}[/]")
            break

        if result.get("outcome") == "skipped_duplicate":
            console.print(f"[yellow]DUPLICATE SKIPPED[/]")
            continue

        allowed = result.get("compliance_allowed", False)
        action = result.get("compliance_action", "N/A")
        reason = result.get("compliance_reason", "")

        if allowed:
            console.print(f"[green]ALLOWED[/] -> Retry scheduled (AI delay: {result.get('ai_delay_hours', 0)}h, confidence: {result.get('ai_confidence', 0):.0%})")
        else:
            console.print(f"[red]BLOCKED[/] -> {action}: {reason}")
            if action == "STEP_UP_LINK":
                console.print(f"  [cyan]Payment link: {result.get('link_url', 'N/A')}[/]")
            elif action == "STOP":
                console.print(f"  [red]Mandate halted - no more retries[/]")
            break

    return result


def run_demo():
    print_header()
    print_scenarios()

    orch = RecoveryOrchestrator(use_ml=False)

    scenarios = [
        ("Scenario 1: Customer A - Standard Auto-Recovery", FailedPaymentEvent(
            subscription_id="sub_CUST_A_001",
            customer_id="CUST_A",
            amount=2499,
            failure_code="INSUFFICIENT_FUNDS",
            merchant_category="SAAS",
            bank="HDFC",
            previous_success_count=12,
            previous_failure_count=1,
        )),
        ("Scenario 2: Customer B - High-Value AFA Block", FailedPaymentEvent(
            subscription_id="sub_CUST_B_001",
            customer_id="CUST_B",
            amount=28000,
            failure_code="PAYMENT_FAILED",
            merchant_category="SAAS",
            bank="ICICI",
            previous_success_count=5,
            previous_failure_count=2,
        )),
        ("Scenario 3: Customer C - Mandate Exhausted", FailedPaymentEvent(
            subscription_id="sub_CUST_C_001",
            customer_id="CUST_C",
            amount=8000,
            failure_code="NETWORK_ERROR",
            merchant_category="OTT_PLATFORM",
            bank="SBI",
            previous_success_count=2,
            previous_failure_count=3,
        )),
    ]

    results = []
    for name, event in scenarios:
        result = run_scenario(name, event, orch)
        results.append((name, result))

    try:
        orch.db.commit()
    except Exception:
        pass

    console.print(f"\n[bold cyan]{'='*60}[/]")
    console.print("[bold]Demo Summary[/]")
    console.print(f"{'='*60}\n")

    summary = Table(title="Results", box=box.DOUBLE)
    summary.add_column("Scenario", style="cyan")
    summary.add_column("Outcome", style="green")
    summary.add_column("Details")

    for name, result in results:
        outcome = result.get("outcome", "unknown")
        action = result.get("compliance_action", "N/A")
        summary.add_row(name.split(": ")[1] if ": " in name else name, outcome.upper(), action)

    console.print(summary)
    console.print(f"\n[dim]All data saved to mandatemind.db | Logs in recovery.log[/]")
    console.print(f"[green]Demo complete![/]")


if __name__ == "__main__":
    run_demo()
