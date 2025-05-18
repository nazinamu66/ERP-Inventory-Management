from django.urls import path
from .views import account_balances_view
from . import views
from .views import customer_ledger_pdf  # Make sure this exists in views.py
from .views import record_supplier_payment, profit_loss_report




app_name = 'accounting'

urlpatterns = [
    path('account-balances/', views.account_balances_view, name='account_balances'),
    path('receive-payment/', views.receive_customer_payment, name='receive_customer_payment'),
    path('api/unpaid-invoices/', views.get_unpaid_invoices, name='get_unpaid_invoices'),
    path('account/<slug:slug>/', views.account_ledger_view, name='account_ledger'),
    path('customers/', views.customer_list_with_balances, name='customer_list'),
    path('customers/<int:customer_id>/ledger/', views.customer_ledger_view, name='customer_ledger'),
    path('customers/<int:customer_id>/ledger/pdf/', customer_ledger_pdf, name='customer_ledger_pdf'),
    path('supplier-balances/', views.supplier_balances, name='supplier_balances'),
    path('suppliers/<int:supplier_id>/ledger/', views.supplier_ledger_view, name='supplier_ledger'),
    path('supplier-payment/', record_supplier_payment, name='record_supplier_payment'),
    path('transfer/', views.record_account_transfer, name='record_account_transfer'),
    path('withdraw/', views.withdraw_funds, name='withdraw_funds'),
    path('deposit/', views.record_account_deposit, name='record_account_deposit'),
    path('record-expense/', views.record_expense, name='record_expense'),
    path('customers/<int:customer_id>/delete/', views.delete_customer, name='delete_customer'),
    path('customers/<int:customer_id>/edit/', views.edit_customer, name='edit_customer'),
    path('expenses/', views.expense_history, name='expense_history'),
    path('profit-loss/', profit_loss_report, name='profit_loss_report'),
    path('profit-loss/pdf/', views.profit_loss_pdf_view, name='profit_loss_pdf'),
    path('profit-loss/detail/', views.profit_loss_detail_report, name='profit_loss_detail_report'),
    path('profit-loss/detail/pdf/', views.profit_loss_detail_pdf_view, name='profit_loss_detail_pdf'),

]

