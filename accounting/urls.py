from django.urls import path
from .views import account_balances_view
from . import views
from .views import customer_ledger_pdf  # Make sure this exists in views.py



app_name = 'accounting'

urlpatterns = [
    path('account-balances/', views.account_balances_view, name='account_balances'),
    path('receive-payment/', views.receive_customer_payment, name='receive_customer_payment'),
    path('api/unpaid-invoices/', views.get_unpaid_invoices, name='get_unpaid_invoices'),
    path('account/<slug:slug>/', views.account_ledger_view, name='account_ledger'),
    path('customers/', views.customer_list_with_balances, name='customer_list'),
    path('customers/<int:customer_id>/ledger/', views.customer_ledger_view, name='customer_ledger'),
    path('customers/<int:customer_id>/ledger/pdf/', customer_ledger_pdf, name='customer_ledger_pdf'),

]

