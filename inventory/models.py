from django.db import models
from users.models import User
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Store(models.Model):
    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class StockAdjustment(models.Model):
    product = models.ForeignKey('Item', on_delete=models.CASCADE)
    quantity = models.IntegerField(help_text="Use negative numbers to decrease stock.")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True, blank=True, default=None)
    reason = models.CharField(max_length=255, help_text="E.g. Damaged items, manual correction, stock added")
    adjusted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item.name}: {self.quantity:+} by {self.adjusted_by}"


class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=20, default='pcs')  # e.g. pcs, kg, litres
    quantity = models.PositiveBigIntegerField(default=0)
    total_quantity = models.PositiveBigIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.sku})"

class Item(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)  
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    sku = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Stock(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='stocks')
    product = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='stocks')
    quantity = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('store', 'product')

    def __str__(self):
        return f"{self.product.name} @ {self.store.name}: {self.quantity}"


class Purchase(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    purchase_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Purchased {self.quantity} of {self.item.name} at {self.store.name}"


class Sale(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    sale_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Sold {self.quantity} of {self.item.name} at {self.store.name}"


class StockTransfer(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    source_store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='transfers_out')
    destination_store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='transfers_in')
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transferred {self.quantity} of {self.item.name} from {self.source_store.name} to {self.destination_store.name}"

class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"PO-{self.id} - {self.supplier.name}"
    
class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} pcs"
