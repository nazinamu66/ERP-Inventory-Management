from django import forms
from django.forms import inlineformset_factory
from .models import SaleReturn, SaleReturnItem
from accounting.models import Account


class SaleReturnForm(forms.ModelForm):
    class Meta:
        model = SaleReturn
        fields = ['reason']


SaleReturnItemFormSet = inlineformset_factory(
    SaleReturn,
    SaleReturnItem,
    fields=['sale_item', 'quantity_returned'],
    extra=0,
    can_delete=False
)


from inventory.models import (
    StockTransfer, Store, Product, StockAdjustment,
    Purchase, PurchaseOrder, PurchaseOrderItem, Supplier,
    Sale, SaleItem, Customer
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
        fields = ['product', 'quantity', 'unit_price']


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
            self.fields['store'].queryset = Store.objects.filter(id=request.user.store.id)
            self.fields['store'].initial = request.user.store

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
            self.fields['store'].queryset = Store.objects.filter(id=request.user.store.id)
            self.fields['store'].initial = request.user.store


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
            self.fields['store'].queryset = Store.objects.filter(id=request.user.store.id)
            self.fields['store'].initial = request.user.store

        self.fields['bank_account'].queryset = Account.objects.filter(type='asset')


class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['product', 'store', 'quantity', 'supplier_name', 'note']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'store': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'supplier_name': forms.TextInput(attrs={'class': 'form-control'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if request and hasattr(request.user, 'role') and request.user.role == 'manager':
            self.fields['store'].queryset = Store.objects.filter(id=request.user.store.id)
            self.fields['store'].initial = request.user.store


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


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'sku', 'description', 'category', 'unit', 'quantity', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


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

        if request and hasattr(request.user, 'role') and request.user.role == 'manager':
            self.fields['source_store'].queryset = Store.objects.filter(id=request.user.store.id)
            self.fields['source_store'].initial = request.user.store
