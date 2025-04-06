# inventory/services/erpnext_service.py

import requests
from django.conf import settings

class ERPNextAPI:
    def __init__(self):
        self.base_url = settings.ERPNEXT_BASE_URL
        self.token = settings.ERPNEXT_TOKEN
        self.headers = {
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json"
        }

    def get_items(self):
        url = f"{self.base_url}/api/resource/Item"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get("data", [])
        except requests.RequestException as e:
            print(f"Error fetching items: {e}")
            return []

    def get_item_details(self, item_code):
        url = f"{self.base_url}/api/resource/Item/{item_code}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get("data")
        except requests.RequestException as e:
            print(f"Error fetching item details: {e}")
            return None
