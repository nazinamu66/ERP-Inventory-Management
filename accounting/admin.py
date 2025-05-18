from django.contrib import admin
from django.db.models import Sum
from .models import Account, Transaction
from .services import calculate_account_balances

from .models import SupplierPayment
admin.site.register(SupplierPayment)

from django.contrib import admin
from .models import SupplierLedger

from .models import ExpenseEntry


@admin.register(SupplierLedger)
class SupplierLedgerAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'transaction', 'amount', 'entry_type', 'created_at')
    list_filter = ('supplier', 'entry_type')
    search_fields = ('transaction__description', 'supplier__name')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'opening_balance', 'calculated_balance')
    prepopulated_fields = {"slug": ("name",)}  # auto-fills slug field in admin


    def calculated_balance(self, obj):
        balances = calculate_account_balances()
        return balances.get(obj, 0.00)

    @admin.display(description='Balance')
    def current_balance(self, obj):
        incoming = obj.transactions_in.aggregate(total=Sum('amount'))['total'] or 0
        outgoing = obj.transactions_out.aggregate(total=Sum('amount'))['total'] or 0
        return obj.opening_balance + incoming - outgoing


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'description', 'amount', 'source_account', 'destination_account', 'created_at')
    list_filter = ('created_at', 'source_account', 'destination_account')
    search_fields = ('description',)
    readonly_fields = ('created_at',)


# accounting/admin.py

@admin.register(ExpenseEntry)
class ExpenseEntryAdmin(admin.ModelAdmin):
    list_display = ('expense_account', 'amount', 'store', 'user', 'date')
    list_filter = ('store', 'expense_account', 'date')
