from django.db.models.signals import post_save
from django.dispatch import receiver
from accounting.models import Transaction, SupplierLedger

@receiver(post_save, sender=Transaction)
def create_supplier_ledger_entry(sender, instance, created, **kwargs):
    if created and instance.supplier:
        # Infer type based on source/destination accounts
        destination_slug = instance.destination_account.slug
        source_slug = instance.source_account.slug

        # If supplier control account is the destination, it's a bill (CREDIT)
        # If supplier control account is the source, it's a payment (DEBIT)
        entry_type = 'credit' if destination_slug == 'accounts-payable' else 'debit'

        SupplierLedger.objects.get_or_create(
            transaction=instance,
            supplier=instance.supplier,
            defaults={
                'amount': instance.amount,
                'entry_type': entry_type,
                'created_at': instance.created_at,
            }
        )
