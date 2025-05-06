from django.core.management.base import BaseCommand
from accounting.models import SupplierLedger


class Command(BaseCommand):
    help = 'Fix incorrect or missing entry_type values in SupplierLedger based on transaction source/destination accounts.'

    def handle(self, *args, **options):
        updated = 0
        skipped = 0

        for entry in SupplierLedger.objects.select_related('transaction').all():
            txn = entry.transaction
            source = txn.source_account.slug
            destination = txn.destination_account.slug

            if source == 'accounts-payable':
                new_type = 'debit'
            elif destination == 'accounts-payable':
                new_type = 'credit'
            else:
                self.stdout.write(self.style.WARNING(
                    f"⚠️ Skipping entry {entry.id}: Not related to supplier control account."
                ))
                skipped += 1
                continue

            if entry.entry_type != new_type:
                entry.entry_type = new_type
                entry.save()
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Fixed {updated} entries. Skipped {skipped} unrelated entries."
        ))
