from .models import Account, Transaction, TransactionLine
from django.db import transaction as db_transaction
from django.db.models import Sum
from django.utils import timezone


# System-defined accounts (slugs will be used for identification)
DEFAULT_ACCOUNTS = [
    {"name": "Undeposited Funds", "slug": "undeposited-funds", "type": "asset"},
    {"name": "Sales Revenue", "slug": "sales-revenue", "type": "revenue"},
    {"name": "Inventory Asset", "slug": "inventory-assets", "type": "asset"},
    {"name": "Cost of Goods Sold", "slug": "cost-of-goods-sold", "type": "expense"},
    {"name": "Accounts Receivable", "slug": "accounts-receivable", "type": "asset"},
    {"name": "Accounts Payable", "slug": "accounts-payable", "type": "liability"},
]


def create_system_accounts():
    """
    Creates essential system accounts with fixed slugs and types.
    If a name exists but slug is missing, it updates the slug.
    """
    created = []
    for acc in DEFAULT_ACCOUNTS:
        existing = Account.objects.filter(name=acc["name"]).first()
        if existing:
            if not existing.slug:
                existing.slug = acc["slug"]
                existing.save(update_fields=["slug"])
            continue

        obj, is_created = Account.objects.get_or_create(
            slug=acc["slug"],
            defaults={"name": acc["name"], "type": acc["type"]}
        )
        if is_created:
            created.append(obj.name)
    return created


def calculate_account_balances():
    """
    Calculates account balances based on account type logic:
    - Assets & Expenses: opening + debits - credits
    - Liabilities, Income, Equity: opening + credits - debits
    """
    balances = {}
    accounts = Account.objects.all()

    for account in accounts:
        debit_total = TransactionLine.objects.filter(account=account).aggregate(
            debit_sum=Sum('debit')
        )['debit_sum'] or 0

        credit_total = TransactionLine.objects.filter(account=account).aggregate(
            credit_sum=Sum('credit')
        )['credit_sum'] or 0

        if account.type in ['asset', 'expense']:
            balance = account.opening_balance + debit_total - credit_total
        elif account.type in ['liability', 'income', 'equity']:
            balance = account.opening_balance + credit_total - debit_total
        else:
            balance = account.opening_balance + debit_total - credit_total

        balances[account] = balance

    return balances


def record_transaction(source_account_slug, destination_account_slug, amount, description=""):
    """
    Creates a double-entry transaction:
    - Credits the source account (identified by slug)
    - Debits the destination account (identified by slug)

    Returns: Transaction instance
    Raises: Account.DoesNotExist if slug is incorrect
    """
    source = Account.objects.get(slug=source_account_slug)
    destination = Account.objects.get(slug=destination_account_slug)

    with db_transaction.atomic():
        txn = Transaction.objects.create(
            source_account=source,
            destination_account=destination,
            amount=amount,
            description=description,
            created_at=timezone.now()
        )

        # Double-entry lines
        TransactionLine.objects.create(transaction=txn, account=destination, debit=amount)
        TransactionLine.objects.create(transaction=txn, account=source, credit=amount)

        return txn

def record_transaction_by_slug(source_slug=None, destination_slug=None, amount=0, description="", supplier=None, is_withdrawal=False, is_deposit=False):
    """
    Create a transaction using slugs instead of account names.
    - For normal transfers: both source and destination slugs are used.
    - For withdrawals: only source_slug is used, and amount is deducted.
    - For deposits: only destination_slug is used, and amount is added.
    """
    from django.utils import timezone
    from django.db import transaction as db_transaction
    from .models import Account, Transaction, TransactionLine

    try:
        source = Account.objects.get(slug=source_slug) if source_slug else None
        destination = Account.objects.get(slug=destination_slug) if destination_slug else None
    except Account.DoesNotExist as e:
        print(f"❌ Account not found: {e}")
        raise

    with db_transaction.atomic():
        if is_withdrawal:
            # For withdrawal, we treat a special destination account like "Owner's Drawings"
            owner_drawings = Account.objects.get_or_create(slug="owners-drawings", defaults={"name": "Owner's Drawings"})[0]
            txn = Transaction.objects.create(
                source_account=source,
                destination_account=owner_drawings,
                amount=amount,
                description=description,
                supplier=supplier,
                created_at=timezone.now()
            )
            TransactionLine.objects.create(transaction=txn, account=source, credit=amount)
            TransactionLine.objects.create(transaction=txn, account=owner_drawings, debit=amount)

        elif is_deposit:
            # Deposit: money enters the business from "Owner's Contribution"
            capital_account = Account.objects.get_or_create(slug="owners-contribution", defaults={"name": "Owner's Contribution"})[0]
            txn = Transaction.objects.create(
                source_account=capital_account,
                destination_account=destination,
                amount=amount,
                description=description,
                supplier=supplier,
                created_at=timezone.now()
            )
            TransactionLine.objects.create(transaction=txn, account=destination, debit=amount)
            TransactionLine.objects.create(transaction=txn, account=capital_account, credit=amount)

        else:
            # Normal transfer between two accounts
            if not source or not destination:
                raise ValueError("Both source and destination must be provided for a transfer.")

            txn = Transaction.objects.create(
                source_account=source,
                destination_account=destination,
                amount=amount,
                description=description,
                supplier=supplier,
                created_at=timezone.now()
            )
            TransactionLine.objects.create(transaction=txn, account=destination, debit=amount)
            TransactionLine.objects.create(transaction=txn, account=source, credit=amount)

        return txn


def reverse_transaction(original_transaction_id, reason="Reversal"):
    """
    Reverses a transaction by creating an equal and opposite entry.
    Returns: the new reversed Transaction instance.
    """
    try:
        original = Transaction.objects.get(id=original_transaction_id)

        with db_transaction.atomic():
            reversed_txn = Transaction.objects.create(
                source_account=original.destination_account,
                destination_account=original.source_account,
                amount=original.amount,
                description=f"REVERSAL: {reason}",
                created_at=timezone.now()
            )

            for line in original.lines.all():
                TransactionLine.objects.create(
                    transaction=reversed_txn,
                    account=line.account,
                    debit=line.credit,
                    credit=line.debit
                )

            return reversed_txn

    except Transaction.DoesNotExist:
        raise ValueError(f"Original transaction #{original_transaction_id} not found.")
