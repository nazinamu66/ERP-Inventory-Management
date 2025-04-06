from django.contrib import admin
from .models import Store, Supplier, Item, Stock, Purchase, Sale, StockTransfer

admin.site.register(Store)
admin.site.register(Supplier)
admin.site.register(Item)
admin.site.register(Stock)
admin.site.register(Purchase)
admin.site.register(Sale)
admin.site.register(StockTransfer)
