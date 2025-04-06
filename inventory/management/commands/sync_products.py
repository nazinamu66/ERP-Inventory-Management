# inventory/management/commands/sync_products.py
from django.core.management.base import BaseCommand
from erp_integration.services import sync_products

class Command(BaseCommand):
    help = 'Syncs products from ERPNext to Django'

    def handle(self, *args, **kwargs):
        self.stdout.write("Syncing products from ERPNext...")
        sync_products()
        self.stdout.write(self.style.SUCCESS("Products synced successfully!"))
