from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .services import calculate_account_balances

@login_required
def account_balances_view(request):
    balances = calculate_account_balances()
    return render(request, 'accounting/account_balances.html', {'balances': balances})
