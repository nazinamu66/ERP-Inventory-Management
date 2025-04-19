from django.db import models
from django.conf import settings
from users.models import User


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
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.sku})"


class Stock(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='stocks')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stocks', default=1)
    quantity = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('store', 'product')

    def __str__(self):
        return f"{self.product.name} @ {self.store.name}: {self.quantity}"



class StockAdjustment(models.Model):
    ADJUSTMENT_CHOICES = [
        ('add', 'Add'),
        ('subtract', 'Subtract'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=1)
    quantity = models.IntegerField(help_text="Enter a positive number only.")
    adjustment_type = models.CharField(max_length=10, choices=ADJUSTMENT_CHOICES, default='add')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True, blank=True, default=None)
    reason = models.CharField(max_length=255, help_text="E.g. Damaged items, manual correction, stock added")
    adjusted_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name}: {self.adjustment_type} {self.quantity} by {self.adjusted_by}"
    

    def save(self, *args, **kwargs):
    # Use passed context if available (e.g., from form or view)
        adjustment_type = getattr(self, 'adjustment_type', None)

    # Default to addition if not passed
        qty = abs(self.quantity)

        if adjustment_type == 'subtract':
            qty = -qty

    # Apply to product
        self.quantity = qty
        super().save(*args, **kwargs)

        self.product.total_quantity = (self.product.total_quantity or 0) + qty
        self.product.save()


class Purchase(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=1)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    purchase_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Purchased {self.quantity} of {self.product.name} at {self.store.name}"


class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=1)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    sale_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Sold {self.quantity} of {self.product.name} at {self.store.name}"


class StockTransfer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=1)
    source_store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='transfers_out')
    destination_store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='transfers_in')
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transferred {self.quantity} of {self.product.name} from {self.source_store.name} to {self.destination_store.name}"


class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"PO-{self.id} - {self.supplier.name}"


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=1)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} pcs"
