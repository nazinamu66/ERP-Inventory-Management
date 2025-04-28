from django.urls import path
from .views import account_balances_view

app_name = 'accounting'

urlpatterns = [
    path('account-balances/', account_balances_view, name='account_balances'),
]
