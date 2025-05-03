from django.db import models
from django.utils import timezone
from django.conf import settings
from django.utils.timezone import now
from inventory.models import Supplier


# ✅ Local imports not required for models within the same file
# ❌ Removed: from inventory.models import Sale
# ❌ Removed: from .accounting_base import Account, Transaction

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return self.name


class Transaction(models.Model):
    source_account = models.ForeignKey(Account, related_name='source_transactions', on_delete=models.CASCADE)
    destination_account = models.ForeignKey(Account, related_name='destination_transactions', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

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
        return f"{self.customer.name} paid ₹{self.amount}"

class SupplierPayment(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)  # Bank or cash account
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(default=now)
    note = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment of {self.amount} to {self.supplier.name} on {self.payment_date}"

 