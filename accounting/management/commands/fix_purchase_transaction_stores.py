# in accounting/management/commands/fix_purchase_transaction_stores.py

from django.core.management.base import BaseCommand
from inventory.models import Purchase
from accounting.models import Transaction

class Command(BaseCommand):
    help = 'Backfill store field in transactions linked to purchases'

    def handle(self, *args, **kwargs):
        updated = 0
        for purchase in Purchase.objects.exclude(transaction__isnull=True):
            txn = purchase.transaction
            if txn and not txn.store:
                txn.store = purchase.store
                txn.save(update_fields=['store'])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f'✅ Updated {updated} purchase-linked transactions.'))
