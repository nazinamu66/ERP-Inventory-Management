from django.db import models
from django.conf import settings
from users.models import User
from django.utils.timezone import now
from django.contrib.auth import get_user_model
import accounting.models as accounting_models
# from accounting.models import Transaction  # add this import


PAYMENT_STATUS_CHOICES = [
    ('paid', 'Paid'),
    ('unpaid', 'Unpaid'),
    ('partial', 'Partially Paid'),
]

PAYMENT_METHOD_CHOICES = [
    ('cash', 'Cash'),
    ('bank', 'Bank Transfer'),
    ('pos', 'POS'),
]


User = get_user_model()

class SaleReturn(models.Model):
    sale = models.ForeignKey('Sale', on_delete=models.CASCADE, related_name='returns')
    returned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    return_date = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)
    total_refunded = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Return #{self.id} for {self.sale.receipt_number}"


class SaleReturnItem(models.Model):
    sale_return = models.ForeignKey(SaleReturn, on_delete=models.CASCADE, related_name='items')
    sale_item = models.ForeignKey('SaleItem', on_delete=models.CASCADE, related_name='return_items')
    quantity_returned = models.PositiveIntegerField()

    def subtotal(self):
        return self.quantity_returned * self.sale_item.unit_price


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


# inventory/models.py

class Store(models.Model):
    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    company_profile = models.ForeignKey(
        CompanyProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stores'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

from django.db import models
from users.models import User

class Quotation(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    quote_number = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True)
    store = models.ForeignKey('Store', on_delete=models.SET_NULL, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    note = models.TextField(blank=True, null=True)

    converted_to_invoice = models.BooleanField(default=False)
    converted_sale = models.OneToOneField(
        'Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quotation_source'
    )
    # models.py (Quotation)
    converted_sale = models.ForeignKey('Sale', null=True, blank=True, on_delete=models.SET_NULL, related_name='from_quotation')


    def __str__(self):
        return f"Quote #{self.quote_number}"

    def total_amount(self):
        return sum(item.subtotal() for item in self.items.all())


class QuotationItem(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.quantity * self.unit_price


class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


from django.core.exceptions import ValidationError
from .utils.barcodes import generate_barcode_image
import os
import uuid


class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True, blank=True)
    barcode = models.CharField(max_length=50, unique=True, blank=True, null=True)
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)  # ✅ NEW
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=20, default='pcs')
    quantity = models.PositiveBigIntegerField(default=0)
    total_quantity = models.PositiveBigIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True, blank=True)
    reorder_level = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='created_products'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='updated_products'
    )

    def clean(self):
        # ✅ Prevent duplicate active product names
        conflict = Product.objects.filter(name__iexact=self.name.strip(), is_active=True)
        if self.pk:
            conflict = conflict.exclude(pk=self.pk)
        if conflict.exists():
            raise ValidationError(f"A product named '{self.name}' already exists and is active.")

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        # ✅ Auto-generate barcode if missing
        if not self.barcode:
            self.barcode = f"INV-{uuid.uuid4().hex[:8].upper()}"

        self.full_clean()  # Validate fields
        super().save(*args, **kwargs)

        # ✅ Generate barcode image only once when first saved
        if is_new:
            output_path = os.path.join(settings.MEDIA_ROOT, 'barcodes', f"{self.pk}.png")
            generate_barcode_image(self.barcode, output_path)

    def __str__(self):
        return f"{self.name} ({self.sku})"


class Stock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    # ✅ NEW: Link to accounting transaction (for reversals)
    transaction = models.ForeignKey(
        'accounting.Transaction',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Reference to the initial inventory transaction"
    )

    class Meta:
        unique_together = ('product', 'store')

    def __str__(self):
        return f"{self.product.name} at {self.store.name}"


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


from django.conf import settings

class Customer(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return self.name
    
from django.utils.crypto import get_random_string

    
class Sale(models.Model):
    SALE_TYPE_CHOICES = [
        ('receipt', 'Sales Receipt'),  # Payment made immediately
        ('invoice', 'Invoice'),        # Credit sale, paid later
    ]

    sale_type = models.CharField(
        max_length=10,
        choices=SALE_TYPE_CHOICES,
        default='receipt'
    )

    # ✅ Only keep this one version of transaction
    transaction = models.OneToOneField(
        'accounting.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sale_record"
    )



    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    sold_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    sale_date = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # ✅ New field
    receipt_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    note = models.TextField(blank=True, null=True)

    def update_payment_status(self):
        self.balance_due = self.total_amount - self.amount_paid
        if self.amount_paid == 0:
            self.payment_status = 'unpaid'
        elif self.amount_paid < self.total_amount:
            self.payment_status = 'partial'
        else:
            self.payment_status = 'paid'
        self.save(update_fields=['payment_status', 'amount_paid', 'balance_due'])
    
    revenue_transaction = models.OneToOneField(
        'accounting.Transaction',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='revenue_sale'
    )
    cogs_transaction = models.OneToOneField(
        'accounting.Transaction',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cogs_sale'
    )
    ...


    def __str__(self):
        return f"{self.customer.name} - {self.receipt_number or 'Unnumbered Sale'}"



class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    # ✅ New field to record cost price at time of sale
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def total_returned(self):
        return sum(item.quantity_returned for item in self.return_items.all())

    @property
    def subtotal(self):
        return self.quantity * self.unit_price
    
    @property
    def profit(self):
        return (self.unit_price - self.cost_price) * self.quantity


    @property
    def total_cost(self):
        return self.quantity * self.cost_price

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

# models.py

from django.apps import apps
class StockTransfer(models.Model):
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=1)
    source_store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='transfers_out')
    destination_store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='transfers_in')
    quantity = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_transfers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')

    # ✅ ADD THIS FIELD
    # Still in inventory/models.py

    transfer_transaction = models.ForeignKey(
        'accounting.Transaction',  # ✅ Use a string instead of importing directly
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='stock_transfers',
        help_text="Linked transaction for accounting purposes"
    )

    def __str__(self):
        return f"{self.quantity} x {self.product.name} from {self.source_store.name} to {self.destination_store.name}"



class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('received', 'Received'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True)  # ✅ add this
    date = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')


class Purchase(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    transaction = models.ForeignKey(
        'accounting.Transaction',  # ← use string-based reference
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )    
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
    expected_sales_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # 🆕 NEW


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
        ('expense', 'Expense Entry'),  # 👈 Add this
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField()
    store = models.ForeignKey(Store, null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.user} | {self.action} | {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
