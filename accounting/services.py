from .models import Account, Transaction, TransactionLine
from django.db import transaction as db_transaction
from django.db.models import Sum
from django.utils import timezone
from accounting.models import SupplierLedger



# System-defined accounts (slugs will be used for identification)
DEFAULT_ACCOUNTS = [
    {"name": "Undeposited Funds", "slug": "undeposited-funds", "type": "asset"},
    {"name": "Sales Revenue", "slug": "sales-revenue", "type": "income"},
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


def calculate_account_balances(store=None):
    """
    Calculates account balances.
    If a store is provided, only considers transactions from that store.

    - Assets & Expenses: opening + debits - credits
    - Liabilities, Income, Equity: opening + credits - debits
    """
    balances = {}
    accounts = Account.objects.all()

    for account in accounts:
        lines = TransactionLine.objects.filter(account=account)

        if store:
            lines = lines.filter(transaction__store=store)

        debit_total = lines.aggregate(debit_sum=Sum('debit'))['debit_sum'] or 0
        credit_total = lines.aggregate(credit_sum=Sum('credit'))['credit_sum'] or 0

        if account.type in ['asset', 'expense']:
            balance = account.opening_balance + debit_total - credit_total
        elif account.type in ['liability', 'income', 'equity']:
            balance = account.opening_balance + credit_total - debit_total
        else:
            balance = account.opening_balance + debit_total - credit_total

        balances[account] = balance

    return balances


def record_transaction(source_account_slug, destination_account_slug, amount, store, description=""):
    """
    Creates a double-entry transaction:
    - Credits the source account (identified by slug)
    - Debits the destination account (identified by slug)

    Returns: Transaction instance
    Raises: Account.DoesNotExist if slug is incorrect
    """
    source = Account.objects.get(slug=source_account_slug, store = store)
    destination = Account.objects.get(slug=destination_account_slug, store = store)

    with db_transaction.atomic():
        txn = Transaction.objects.create(
            source_account=source,
            destination_account=destination,
            amount=amount,
            description=description,
            created_at=timezone.now(),
            store=store 

        )

        # Double-entry lines
        TransactionLine.objects.create(transaction=txn, account=destination, debit=amount)
        TransactionLine.objects.create(transaction=txn, account=source, credit=amount)

        return txn


def record_transaction_by_slug(
    source_slug=None,
    destination_slug=None,
    amount=0,
    description="",
    supplier=None,
    is_withdrawal=False,
    is_deposit=False,
    store=None  # ← NEW!
):
    """
    Create a transaction using slugs instead of account names.
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
            owner_drawings = Account.objects.get_or_create(slug="owners-drawings", defaults={"name": "Owner's Drawings"})[0]
            txn = Transaction.objects.create(
                source_account=source,
                destination_account=owner_drawings,
                amount=amount,
                description=description,
                supplier=supplier,
                created_at=timezone.now(),
                store=store  # ← include store
            )
            TransactionLine.objects.create(transaction=txn, account=source, credit=amount)
            TransactionLine.objects.create(transaction=txn, account=owner_drawings, debit=amount)

        elif is_deposit:
            capital_account = Account.objects.get_or_create(slug="owners-contribution", defaults={"name": "Owner's Contribution"})[0]
            txn = Transaction.objects.create(
                source_account=capital_account,
                destination_account=destination,
                amount=amount,
                description=description,
                supplier=supplier,
                created_at=timezone.now(),
                store=store  # ← include store
            )
            TransactionLine.objects.create(transaction=txn, account=destination, debit=amount)
            TransactionLine.objects.create(transaction=txn, account=capital_account, credit=amount)

        else:
            if not source or not destination:
                raise ValueError("Both source and destination must be provided for a transfer.")

            txn = Transaction.objects.create(
                source_account=source,
                destination_account=destination,
                amount=amount,
                description=description,
                supplier=supplier,
                created_at=timezone.now(),
                store=store  # ← include store
            )
            TransactionLine.objects.create(transaction=txn, account=destination, debit=amount)
            TransactionLine.objects.create(transaction=txn, account=source, credit=amount)

        return txn


def reverse_transaction(original_transaction_id, reason="Reversal"):
    from accounting.models import Transaction, TransactionLine, SupplierLedger

    try:
        original = Transaction.objects.get(id=original_transaction_id)

        with db_transaction.atomic():
            # Create the reversal transaction
            reversed_txn = Transaction.objects.create(
                source_account=original.destination_account,
                destination_account=original.source_account,
                amount=original.amount,
                description=f"REVERSAL: {reason}",
                created_at=timezone.now(),
                supplier=original.supplier,
                store=original.store
            )

            # Create reversal lines
            for line in original.lines.all():
                TransactionLine.objects.create(
                    transaction=reversed_txn,
                    account=line.account,
                    debit=line.credit,
                    credit=line.debit
                )

            # Handle supplier ledger reversal is in signals.py
            
    except Transaction.DoesNotExist:
        raise ValueError(f"Original transaction #{original_transaction_id} not found.")
