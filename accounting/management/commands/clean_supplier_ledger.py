from django.core.management.base import BaseCommand
from accounting.models import SupplierLedger
from collections import defaultdict

class Command(BaseCommand):
    help = 'Clean duplicate SupplierLedger entries (keeps only one per transaction)'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Starting supplier ledger cleanup...")

        duplicates = defaultdict(list)
        for entry in SupplierLedger.objects.select_related('transaction', 'supplier'):
            duplicates[entry.transaction_id].append(entry)

        removed_count = 0

        for txn_id, entries in duplicates.items():
            if len(entries) > 1:
                self.stdout.write(f"🧾 Transaction {txn_id} has {len(entries)} ledger entries")

                txn = entries[0].transaction
                correct_entry_type = 'credit'
                if txn.description and txn.description.lower().startswith('reversal'):
                    correct_entry_type = 'debit'

                kept = None
                for entry in entries:
                    if entry.entry_type == correct_entry_type and not kept:
                        kept = entry
                    else:
                        self.stdout.write(
                            f"  ❌ Deleting duplicate: {entry.entry_type} ₹{entry.amount} for {entry.supplier.name}"
                        )
                        entry.delete()
                        removed_count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Cleanup complete. {removed_count} duplicate ledger entries removed."))
