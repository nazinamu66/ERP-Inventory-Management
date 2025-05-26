from django.urls import path
from .views import account_balances_view
from . import views
from .views import customer_ledger_pdf  # Make sure this exists in views.py
from .views import record_supplier_payment, profit_loss_report, general_ledger_view




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
    path('reports/trial-balance/', views.trial_balance_view, name='trial_balance'),
    path('ledger/', general_ledger_view, name='general_ledger'),
    path('balance-sheet/', views.balance_sheet_view, name='balance_sheet'),
    path('balance-sheet/pdf/', views.balance_sheet_pdf_view, name='balance_sheet_pdf'),
    path('suppliers/<int:supplier_id>/ledger/pdf/', views.supplier_ledger_pdf, name='supplier_ledger_pdf'),
    path('customers/aging/', views.customer_aging_report_view, name='customer_aging_report'),
    path('customers/aging/pdf/', views.customer_aging_report_pdf, name='customer_aging_report_pdf'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:notification_id>/go/', views.notification_redirect, name='notification_redirect'),




]

