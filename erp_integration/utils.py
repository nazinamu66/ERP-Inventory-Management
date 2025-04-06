import requests
from .config import ERP_API_URL, ERP_API_KEY, ERP_API_SECRET
from django.conf import settings
# erp_integration/utils.py
import requests
from .config import ERP_API_URL, ERP_API_KEY, ERP_API_SECRET
from inventory.models import Product

def sync_products_from_erp():
    url = f"{ERP_API_URL}/api/resource/Item"
    headers = {
        "Authorization": f"token {ERP_API_KEY}:{ERP_API_SECRET}"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        items = data.get('data', [])  # ERPNext returns list inside 'data'

        for item_data in items:
            product, created = Product.objects.update_or_create(
                sku=item_data.get('item_code'),  # SKU is usually 'item_code'
                defaults={
                    'name': item_data.get('item_name'),
                    'stock': item_data.get('stock_qty', 0),  # Stock might be stored differently
                    'price': item_data.get('standard_rate', 0.00)
                }
            )
            print(f"Product {'created' if created else 'updated'}: {product.name}")
    else:
        print(f"Failed to fetch products from ERPNext: {response.text}")
def fetch_erp_products():
    url = f"{ERP_API_URL}/api/resource/Product"
    headers = {"Authorization": f"token {ERP_API_KEY}:{ERP_API_SECRET}"}
    response = requests.get(url, headers=headers)
    return response.json()

if __name__ == "__main__":
    print(fetch_erp_products())  # Run this manually for debugging



ERP_API_URL = settings.ERP_API_URL
ERP_API_KEY = settings.ERP_API_KEY
ERP_API_SECRET = settings.ERP_API_SECRET


def get_erp_data(endpoint):
    """Fetch data from ERPNext API"""
    url = f"{ERP_API_URL}{endpoint}"
    headers = {
        "Authorization": f"token {ERP_API_KEY}:{ERP_API_SECRET}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    return response.json()

# Test function
if __name__ == "__main__":
    print(get_erp_data("/method/ping"))
