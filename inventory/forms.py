from django import forms
from inventory.models import StockTransfer, Store, Item


class StockTransferForm(forms.ModelForm):
    class Meta:
        model = StockTransfer
        fields = ['item', 'source_store', 'destination_store', 'quantity']
