import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

import json
import random
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.models.database import SessionLocal, NotificationRecord


console = Console()

WHATSAPP_TEMPLATES = {
    "pre_debit_notice": {
        "title": "Pre-Debit Notice (24h)",
        "icon": " ",
        "body": "Dear {customer_id},\n\nA payment of Rs.{amount} will be debited from your account for subscription {subscription_id} on {date}.\n\nTo cancel this mandate, visit: {cancel_url}\n\n- RecoverX",
    },
    "retry_notification": {
        "title": "Payment Retry Scheduled",
        "icon": " ",
        "body": "Dear {customer_id},\n\nWe will retry your payment of Rs.{amount} for {subscription_id} at {retry_time}.\n\nNo action needed if your account has sufficient balance.\n\n- RecoverX",
    },
    "stepup_link": {
        "title": "Action Required - Verification",
        "icon": " ",
        "body": "Dear {customer_id},\n\nYour payment of Rs.{amount} requires additional verification as per RBI guidelines.\n\nComplete payment here: {payment_url}\n\nThis link expires in 24 hours.\n\n- RecoverX",
    },
    "mandate_exhausted": {
        "title": "Subscription Paused",
        "icon": " ",
        "body": "Dear {customer_id},\n\nYour subscription {subscription_id} has been paused after multiple payment failures.\n\nPlease update your payment method or contact support.\n\n- RecoverX",
    },
}


SAMPLE_CUSTOMERS = [
    {"id": "cust_rahul_001", "name": "Rahul Sharma"},
    {"id": "cust_priya_002", "name": "Priya Patel"},
    {"id": "cust_ankit_003", "name": "Ankit Kumar"},
    {"id": "cust_neha_004", "name": "Neha Singh"},
    {"id": "cust_vikram_005", "name": "Vikram Rao"},
]


def generate_sample_notification(template: str, customer: dict, amount: int, subscription_id: str) -> dict:
    tpl = WHATSAPP_TEMPLATES[template]

    kwargs = {
        "customer_id": customer["id"],
        "amount": f"{amount:,}",
        "subscription_id": subscription_id,
        "date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "retry_time": (datetime.now() + timedelta(hours=random.randint(1, 12))).strftime("%H:%M IST"),
        "payment_url": f"https://rzp.io/i/abc{random.randint(100, 999)}",
        "cancel_url": f"https://rzp.io/cancel/{subscription_id}",
    }

    body = tpl["body"].format(**kwargs)

    payload = {
        "channel": "whatsapp",
        "template": template,
        "title": tpl["title"],
        "body": body,
        "recipient": customer["id"],
        "amount": amount,
        "subscription_id": subscription_id,
        "timestamp": datetime.now().isoformat(),
    }

    return payload


def store_notification(db, event_id: str, payload: dict):
    db.add(NotificationRecord(
        id=f"NOTIF_{event_id}",
        event_id=event_id,
        channel=payload.get("channel", "whatsapp"),
        template=payload.get("template", ""),
        recipient=payload.get("recipient", ""),
        payload=json.dumps(payload),
    ))
    db.commit()


def display_notification(payload: dict):
    template = payload.get("template", "")
    tpl = WHATSAPP_TEMPLATES.get(template, {})
    icon = tpl.get("icon", " ")

    table = Table(show_header=False, border_style="blue")
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    table.add_row("To", payload.get("recipient", ""))
    table.add_row("Template", template)
    table.add_row("Amount", f"Rs.{payload.get('amount', 0):,}")

    console.print()
    console.print(Panel(
        payload.get("body", ""),
        title=f"{icon} {tpl.get('title', 'Notification')}",
        subtitle=f"Sent at {payload.get('timestamp', '')}",
        border_style="green",
    ))
    console.print(table)


def run_simulation(count: int = 5):
    console.print("\n[bold cyan]RecoverX WhatsApp Notification Simulator[/bold cyan]\n")

    db = SessionLocal()

    templates = list(WHATSAPP_TEMPLATES.keys())
    generated = []

    for i in range(count):
        customer = random.choice(SAMPLE_CUSTOMERS)
        template = random.choice(templates)
        amount = random.choice([999, 1499, 2499, 4999, 9999, 14999, 24999])
        sub_id = f"sub_{customer['id'].split('_')[1]}_{random.randint(100, 999)}"

        payload = generate_sample_notification(template, customer, amount, sub_id)
        event_id = f"EVT_SIM_{int(datetime.now().timestamp())}_{i}"

        store_notification(db, event_id, payload)
        display_notification(payload)

        generated.append(payload)

    console.print(f"\n[bold green]Generated {count} notifications and stored in database.[/bold green]\n")

    summary = Table(title="Summary", border_style="cyan")
    summary.add_column("Template", style="cyan")
    summary.add_column("Count", style="green")

    from collections import Counter
    template_counts = Counter(p["template"] for p in generated)
    for tpl, cnt in template_counts.items():
        summary.add_row(tpl, str(cnt))

    console.print(summary)

    db.close()
    return generated


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RecoverX WhatsApp Notification Simulator")
    parser.add_argument("-n", "--count", type=int, default=5, help="Number of notifications to generate")
    args = parser.parse_args()

    run_simulation(args.count)
