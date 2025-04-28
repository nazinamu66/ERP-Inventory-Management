from django.db import models
from django.conf import settings
from django.utils import timezone


class Account(models.Model):
    ACCOUNT_TYPES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
    ]

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=50, choices=ACCOUNT_TYPES)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and self.opening_balance > 0:
            # Only create Opening Balance transaction once!
            from .models import Transaction
            Transaction.objects.create(
                description="Opening Balance",
                amount=self.opening_balance,
                destination_account=self,
                created_at=timezone.now()
            )

class Transaction(models.Model):
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    source_account = models.ForeignKey(
        Account, 
        related_name='transactions_out',  # 👈 outgoing transactions
        on_delete=models.CASCADE
    )
    destination_account = models.ForeignKey(
        Account,
        related_name='transactions_in',  # 👈 incoming transactions
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.description} ({self.amount})"


class TransactionLine(models.Model):
    transaction = models.ForeignKey(Transaction, related_name='lines', on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.account.name}: Dr {self.debit} / Cr {self.credit}"
