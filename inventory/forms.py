from django import forms
from inventory.models import StockTransfer, Store, Product, StockAdjustment

class StockAdjustmentForm(forms.ModelForm):
    ADJUSTMENT_CHOICES = [
        ('add', 'Add'),
        ('subtract', 'Subtract')
    ]

    adjustment_type = forms.ChoiceField(
        choices=ADJUSTMENT_CHOICES,
        widget=forms.RadioSelect,  # Or Select
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
