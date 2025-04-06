from django.core.management.base import BaseCommand
from inventory.models import Supplier
from inventory.integrations.erpnext.sync import fetch_suppliers_from_erpnext

class Command(BaseCommand):
    help = "Sync suppliers from ERPNext into the local database"

    def handle(self, *args, **kwargs):
        erp_suppliers = fetch_suppliers_from_erpnext()
        for data in erp_suppliers:
            supplier, created = Supplier.objects.update_or_create(
                name=data['name'],
                defaults={
                    'contact_email': data.get('email'),
                    'contact_phone': data.get('phone'),
                    'address': data.get('address'),
                }
            )
            self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'}: {supplier.name}"))
