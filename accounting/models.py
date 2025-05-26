from django.db import models
from django.utils import timezone
from django.conf import settings
from django.utils.timezone import now
from inventory.models import Supplier
from inventory.models import Store
from django.contrib.auth import get_user_model



class SupplierLedger(models.Model):
    supplier = models.ForeignKey('inventory.Supplier', on_delete=models.CASCADE, related_name='ledger_entries')
    transaction = models.ForeignKey('accounting.Transaction', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    entry_type = models.CharField(max_length=10, choices=(('debit', 'Debit'), ('credit', 'Credit')))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.supplier.name} - {self.entry_type} - {self.amount}"



# ✅ Local imports not required for models within the same file
# ❌ Removed: from inventory.models import Sale
# ❌ Removed: from .accounting_base import Account, Transaction

from django.utils.text import slugify

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('bank', 'Bank'),
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True, blank=True)  # allow blank, but generate automatically
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Transaction(models.Model):
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    store = models.ForeignKey(Store, null=True, blank=True, on_delete=models.SET_NULL)

    source_account = models.ForeignKey(Account, null=True, blank=True, related_name='outgoing_transactions', on_delete=models.SET_NULL)
    destination_account = models.ForeignKey(Account, null=True, blank=True, related_name='incoming_transactions', on_delete=models.SET_NULL)
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.SET_NULL)  # if applicable


    def __str__(self):
        return f"{self.description} - {self.amount}"


class TransactionLine(models.Model):
    transaction = models.ForeignKey(Transaction, related_name='lines', on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.account.name} (D:{self.debit}, C:{self.credit})"


class CustomerPayment(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
    ]

    customer = models.ForeignKey('inventory.Customer', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    bank_account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL)
    remarks = models.TextField(blank=True, null=True)
    transaction = models.ForeignKey(Transaction, null=True, blank=True, on_delete=models.SET_NULL)
    invoice = models.ForeignKey('inventory.Sale', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.name} paid ₦{self.amount}"

from decimal import Decimal

class SupplierPayment(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    
    payment_date = models.DateField()
    note = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    transaction = models.ForeignKey(
        'accounting.Transaction',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment of {self.amount} to {self.supplier.name} on {self.payment_date}"


class ExpenseEntry(models.Model):
    expense_account = models.ForeignKey(Account, related_name='expenses', on_delete=models.CASCADE)
    payment_account = models.ForeignKey(Account, related_name='payments', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)

    user = models.ForeignKey(
        get_user_model(), 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='expenses_as_user'  # 👈 define unique related_name
    )
    
    recorded_by = models.ForeignKey(
        get_user_model(), 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='expenses_recorded'  # 👈 define unique related_name
    )

    def __str__(self):
        return f"{self.expense_account.name} - ₦{self.amount}"


# accounting/models.py

from django.conf import settings
from django.db import models

class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"  # 🔧 Add this line
    )
    message = models.TextField()
    url = models.URLField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"🔔 Notification for {self.user.username}"

    def short_message(self):
        return self.message[:50] + ('...' if len(self.message) > 50 else '')
