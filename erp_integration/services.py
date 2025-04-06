import os
import requests
from django.conf import settings
from django.core.wsgi import get_wsgi_application
# erp_integration/services.py
from .utils import sync_products_from_erp

def sync_products():
    sync_products_from_erp()

if __name__ == "__main__":
    sync_products()


# Ensure settings are loaded
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()

def ping_erp():
    """Check if ERPNext API is reachable"""
    headers = {
        "Authorization": f"token {settings.ERP_API_KEY}:{settings.ERP_API_SECRET}"
    }
    response = requests.get(f"{settings.ERP_API_URL}/api/method/ping", headers=headers)
    return response.json()

if __name__ == "__main__":
    print(ping_erp())  # For testing
