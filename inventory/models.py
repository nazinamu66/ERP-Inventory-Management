from django.db import models
from django.conf import settings
from users.models import User
from django.utils.timezone import now



class CompanyProfile(models.Model):
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    address = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name



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


class Customer(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

from django.utils.crypto import get_random_string

class BankAccount(models.Model):
    name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=100, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


    
class Sale(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('unpaid', 'Unpaid'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('pos', 'POS'),
        ('other', 'Other'),
    ]
    receipt_number = models.CharField(max_length=255, unique=True, blank=True, null=True)
    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    sold_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='paid')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    bank = models.ForeignKey('BankAccount', on_delete=models.SET_NULL, null=True, blank=True)  # 👈 Add this
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)


    note = models.TextField(blank=True, null=True)
    sale_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sale #{self.id} - {self.customer} - {self.payment_status}"
    

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = "RCPT-" + get_random_string(8).upper()
        super().save(*args, **kwargs)


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

class StockTransfer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=1)
    source_store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='transfers_out')
    destination_store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='transfers_in')
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transferred {self.quantity} of {self.product.name} from {self.source_store.name} to {self.destination_store.name}"


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('received', 'Received'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')


class Purchase(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    supplier_name = models.CharField(max_length=255, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    purchased_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    purchase_date = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.quantity} of {self.product.name} for {self.store.name} on {self.purchase_date.strftime('%Y-%m-%d')}"



class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=1)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantity * self.unit_price


    def __str__(self):
        return f"{self.product.name} - {self.quantity} pcs"
    


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('adjustment', 'Stock Adjustment'),
        ('transfer', 'Stock Transfer'),
        ('create_user', 'User Created'),
        ('delete_user', 'User Deleted'),
        # Add more actions later as needed
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField()
    timestamp = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.user} | {self.action} | {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"