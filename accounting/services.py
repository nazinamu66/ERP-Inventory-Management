from .models import Account, Transaction
from django.db.models import Sum
from django.db import models
from django.db import transaction as db_transaction
from django.utils import timezone



# accounting/services.py

def calculate_account_balances():
    balances = {}

    accounts = Account.objects.all()
    for account in accounts:
        incoming = Transaction.objects.filter(destination_account=account).aggregate(total=models.Sum('amount'))['total'] or 0
        outgoing = Transaction.objects.filter(source_account=account).aggregate(total=models.Sum('amount'))['total'] or 0

        # 🔥 NEW FORMULA 🔥
        balance = account.opening_balance + (incoming - outgoing)
        balances[account] = balance

    return balances


def record_transaction(source_account_name, destination_account_name, amount, description=""):
    """
    Proper double-entry transaction recording.
    - Debit destination account
    - Credit source account
    """
    try:
        source = Account.objects.get(name=source_account_name)
    except Account.DoesNotExist:
        raise ValueError(f"Source Account '{source_account_name}' not found.")

    try:
        destination = Account.objects.get(name=destination_account_name)
    except Account.DoesNotExist:
        raise ValueError(f"Destination Account '{destination_account_name}' not found.")

    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    with db_transaction.atomic():
        # Credit Source Account (outgoing money)
        Transaction.objects.create(
            source_account=source,
            destination_account=destination,
            amount=amount,
            description=description,
            created_at=timezone.now()
        )

        # Debit Destination Account (incoming money)
        Transaction.objects.create(
            source_account=destination,
            destination_account=source,
            amount=-amount,
            description=f"Auto reverse: {description}",
            created_at=timezone.now()
        )