from django import forms
from inventory.models import StockTransfer, Store, Item
from .models import Product
from .models import StockAdjustment

from django import forms
from .models import StockAdjustment, Product, Store

class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockAdjustment
        fields = ['product', 'store', 'quantity', 'reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity <= 0:
            raise forms.ValidationError("Quantity must be a positive number.")
        return quantity


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'sku', 'description', 'category', 'unit', 'quantity' ,'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class StockTransferForm(forms.ModelForm):
    class Meta:
        model = StockTransfer
        fields = ['item', 'source_store', 'destination_store', 'quantity']
