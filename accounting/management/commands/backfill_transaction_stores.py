from django.core.management.base import BaseCommand
from accounting.models import Transaction
from inventory.models import Sale, Purchase
from django.db import transaction as db_transaction

class Command(BaseCommand):
    help = 'Backfills store on transactions using related Sale or Purchase objects'

    def handle(self, *args, **kwargs):
        updated_count = 0
        skipped_count = 0

        with db_transaction.atomic():
            for txn in Transaction.objects.filter(store__isnull=True):
                store = None

                # Try to find a Sale linked to this transaction
                sale = Sale.objects.filter(transaction=txn).first()
                if sale and sale.store:
                    store = sale.store

                # Add similar logic for other models if needed later

                if store:
                    txn.store = store
                    txn.save(update_fields=["store"])
                    updated_count += 1
                else:
                    skipped_count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Updated {updated_count} transaction(s) with store info."))
        if skipped_count:
            self.stdout.write(self.style.WARNING(f"⚠️ Skipped {skipped_count} transaction(s) with no linked Sale."))
