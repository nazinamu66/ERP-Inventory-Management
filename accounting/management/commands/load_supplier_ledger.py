# accounting/management/commands/load_supplier_ledger.py

from django.core.management.base import BaseCommand
from accounting.models import Transaction, SupplierLedger
from inventory.models import Supplier, PurchaseOrder


def fix_missing_transaction_suppliers():
    updated = 0
    for txn in Transaction.objects.filter(supplier__isnull=True):
        if 'PO-' in txn.description:
            try:
                po_id = int(txn.description.split("PO-")[1].split()[0])
                po = PurchaseOrder.objects.get(id=po_id)
                txn.supplier = po.supplier
                txn.save()
                updated += 1
            except Exception as e:
                print(f"⚠️ Could not update txn {txn.id}: {e}")
    print(f"🔧 Fixed {updated} transactions with missing suppliers.")


class Command(BaseCommand):
    help = 'Load past transactions into the Supplier Ledger.'

    def handle(self, *args, **kwargs):
        fix_missing_transaction_suppliers()  # 🔧 Optional: fix any missing suppliers

        created = 0
        skipped = 0

        for txn in Transaction.objects.exclude(supplier=None):
            if SupplierLedger.objects.filter(transaction=txn).exists():
                skipped += 1
                continue

            SupplierLedger.objects.create(
                supplier=txn.supplier,
                transaction=txn,
                amount=txn.amount,
                entry_type='credit',
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ Supplier Ledger loading complete: {created} created, {skipped} skipped.'))
