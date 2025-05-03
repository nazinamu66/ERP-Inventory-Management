from django.contrib import admin
from django.db.models import Sum
from .models import Account, Transaction
from .services import calculate_account_balances

from .models import SupplierPayment
admin.site.register(SupplierPayment)



@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'opening_balance', 'calculated_balance')

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
