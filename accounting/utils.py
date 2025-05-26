from django.db.models import Sum
from .models import Account

def get_balance_sheet_context(store=None):
    """
    Returns context dictionary for the balance sheet view or export.
    Groups accounts into Assets, Liabilities, and Equity with balances.
    """
    # Get all accounts (filter by store if needed)
    if store:
        accounts = Account.objects.filter(transactionline__transaction__store=store).distinct()
    else:
        accounts = Account.objects.all()

    assets = []
    liabilities = []
    equity = []

    total_assets = total_liabilities = total_equity = 0

    for acc in accounts:
        lines = acc.transactionline_set.all()
        if store:
            lines = lines.filter(transaction__store=store)

        balance = lines.aggregate(
            debit=Sum('debit'),
            credit=Sum('credit')
        )
        debit = balance['debit'] or 0
        credit = balance['credit'] or 0
        net = debit - credit

        acc_data = {'name': acc.name, 'balance': net}

        if acc.type == 'asset':
            assets.append(acc_data)
            total_assets += net
        elif acc.type == 'liability':
            liabilities.append(acc_data)
            total_liabilities += net
        elif acc.type == 'equity':
            equity.append(acc_data)
            total_equity += net

    return {
        'assets': assets,
        'liabilities': liabilities,
        'equity': equity,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
    }

# notifications/utils.py
from django.contrib.auth import get_user_model
from accounting.models import Notification  # adjust if your model is elsewhere

def notify_users(users, message, url=None):
    for user in users:
        Notification.objects.create(
            user=user,
            message=message,
            url=url  # ✅ match field in model
        )
