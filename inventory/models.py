from django.db import models
from users.models import User
# inventory/models.py


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Store(models.Model):
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=255)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_stores')

    def __str__(self):
        return self.name



class Supplier(models.Model):
    name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name
    class Meta:
        managed = False  # ✅ Don't let Django manage this table
        db_table = 'tabSupplier'  # 🧠 Match ERPNext's actual table name

class Product(models.Model):
    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Item(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    sku = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Stock(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    class Meta:
        unique_together = ("item", "store")

    def __str__(self):
        return f"{self.item.name} - {self.store.name}"


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
    transfer_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Transferred {self.quantity} of {self.item.name} from {self.source_store.name} to {self.destination_store.name}"

class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"PO-{self.id} - {self.supplier.name}"
    
class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} pcs"
