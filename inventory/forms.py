from django import forms
from django.forms import inlineformset_factory
from .models import SaleReturn, SaleReturnItem
from accounting.models import Account
from django.forms import BaseInlineFormSet
from django.core.exceptions import ValidationError
from inventory.models import (
    StockTransfer, Store, Product, StockAdjustment,
    Purchase, PurchaseOrder, PurchaseOrderItem, Supplier,
    Sale, SaleItem, Customer
)


class SaleReturnForm(forms.ModelForm):
    class Meta:
        model = SaleReturn
        fields = ['reason']





class BaseSaleReturnItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        for form in self.forms:
            if form.cleaned_data:
                sale_item = form.cleaned_data.get('sale_item')
                return_qty = form.cleaned_data.get('quantity_returned', 0)

                if return_qty < 0:
                    raise ValidationError("Return quantity cannot be negative.")

                already_returned = sale_item.total_returned()
                max_returnable = sale_item.quantity - already_returned

                if return_qty > max_returnable:
                    raise ValidationError(
                        f"Cannot return more than available. {sale_item.product.name}: Max {max_returnable}"
                    )

SaleReturnItemFormSet = inlineformset_factory(
    SaleReturn,
    SaleReturnItem,
    fields=['sale_item', 'quantity_returned'],
    extra=0,
    can_delete=False,
    formset=BaseSaleReturnItemFormSet
)


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'email', 'phone', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_email', 'contact_phone', 'address']


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier']


class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ['product', 'quantity', 'unit_price', 'expected_sales_price']


class SaleForm(forms.ModelForm):
    bank_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(type='bank'),
        required=False,
        label="Select Bank Account"
    )

    class Meta:
        model = Sale
        fields = [
            'customer', 'store', 'payment_status', 'payment_method',
            'bank_account', 'amount_paid', 'note'
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'store': forms.Select(attrs={'class': 'form-control'}),
            'payment_status': forms.Select(attrs={'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'bank_account': forms.Select(attrs={'class': 'form-control'}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if request and hasattr(request.user, 'role') and request.user.role in ['manager', 'staff', 'sales', 'clerk']:
            self.fields['store'].queryset = request.user.stores.all()
            self.fields['store'].initial = request.user.get_active_store(request)

        self.fields['bank_account'].queryset = Account.objects.filter(type='bank')

# ✅ Using "form" as prefix to match HTML/JS
SaleItemFormSet = inlineformset_factory(
    Sale,
    SaleItem,
    fields=['product', 'quantity', 'unit_price'],
    extra=1,
    can_delete=True
)

# inventory/forms.py

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['customer', 'store', 'note']  # Invoices don’t need payment info yet

        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'store': forms.Select(attrs={'class': 'form-control'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if request and hasattr(request.user, 'role') and request.user.role in ['manager', 'staff', 'sales', 'clerk']:
            self.fields['store'].queryset = request.user.stores.all()
            self.fields['store'].initial = request.user.get_active_store(request)


class SaleReceiptForm(forms.ModelForm):
    bank_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(type='asset'),
        required=False,
        label="Select Bank Account"
    )

    class Meta:
        model = Sale
        fields = [
            'customer', 'store', 'payment_method', 'bank_account', 'note'
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'store': forms.Select(attrs={'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'bank_account': forms.Select(attrs={'class': 'form-control'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if request and hasattr(request.user, 'role') and request.user.role in ['manager', 'staff', 'sales', 'clerk']:
            self.fields['store'].queryset = request.user.stores.all()
            self.fields['store'].initial = request.user.get_active_store(request)

        self.fields['bank_account'].queryset = Account.objects.filter(type='asset')


class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['product', 'store', 'quantity', 'supplier', 'note']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'store': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'supplier': forms.TextInput(attrs={'class': 'form-control'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if request and hasattr(request.user, 'role') and request.user.role == 'manager':
            self.fields['store'].queryset = request.user.stores.all()
            self.fields['store'].initial = request.user.get_active_store(request)


class StockAdjustmentForm(forms.ModelForm):
    ADJUSTMENT_CHOICES = [
        ('add', 'Add'),
        ('subtract', 'Subtract')
    ]

    adjustment_type = forms.ChoiceField(
        choices=ADJUSTMENT_CHOICES,
        widget=forms.RadioSelect,
        required=True
    )

    class Meta:
        model = StockAdjustment
        fields = ['product', 'quantity', 'store', 'reason', 'adjustment_type']
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 1}),
        }

    def clean_quantity(self):
        qty = self.cleaned_data['quantity']
        if qty <= 0:
            raise forms.ValidationError("Please enter a positive number.")
        return qty


class ProductWithStockForm(forms.ModelForm):
    starting_quantity = forms.IntegerField(required=False, min_value=0, label="Initial Quantity")
    cost_price = forms.DecimalField(required=False, max_digits=12, decimal_places=2, label="Initial Cost Price")
    store = forms.ModelChoiceField(queryset=Store.objects.all(), required=False)

    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'unit', 'reorder_level', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Add SKU as readonly on edit
        if self.instance and self.instance.pk:
            self.fields['sku'] = forms.CharField(
                label="SKU",
                initial=self.instance.sku,
                required=False,
                widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control'})
            )

        if user and not user.is_superuser:
            self.fields['store'].queryset = user.stores.all()


class StockTransferForm(forms.ModelForm):
    class Meta:
        model = StockTransfer
        fields = ['product', 'source_store', 'destination_store', 'quantity']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'source_store': forms.Select(attrs={'class': 'form-control'}),
            'destination_store': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        user = request.user if request else None
        is_admin = user.is_superuser if user else False

        if is_admin:
            stores = Store.objects.filter(is_active=True)
        else:
            stores = user.stores.filter(is_active=True)

        self.fields['source_store'].queryset = stores

        # ✅ Destination = All stores with same company_profile as user's first store
        company_profile = stores.first().company_profile if stores.exists() else None
        self.fields['destination_store'].queryset = Store.objects.filter(
            is_active=True,
            company_profile=company_profile
        )

from django import forms
from .models import Quotation, QuotationItem
from django.forms import inlineformset_factory

class QuotationForm(forms.ModelForm):
    class Meta:
        model = Quotation
        fields = ['customer', 'store', 'note']


QuotationItemFormSet = inlineformset_factory(
    Quotation,
    QuotationItem,
    fields=['product', 'quantity', 'unit_price'],
    extra=1,
    can_delete=True,
    widgets={
        'product': forms.Select(attrs={'class': 'form-control'}),
        'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
        'unit_price': forms.NumberInput(attrs={'class': 'form-control'}),
    }
)
