from django import forms
from users.models import User
from inventory.models import Store

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'username', 'email', 'role', 'store',
            'is_active', 'can_view_transfers',
            'can_adjust_stock', 'can_transfer_stock'
        ]
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'store': forms.Select(attrs={'class': 'form-control'}),
        }
