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
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'store': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(),
            'can_view_transfers': forms.CheckboxInput(),
            'can_adjust_stock': forms.CheckboxInput(),
            'can_transfer_stock': forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # If the form was rendered for a manager, limit role and store fields
        if request and hasattr(request, 'user') and request.user.role == 'manager':
            # Prevent selecting admin or manager
            restricted_roles = [('staff', 'Store Staff'), ('clerk', 'Inventory Clerk'), ('sales', 'Sales Staff')]
            self.fields['role'].choices = restricted_roles

            # Lock to manager's store
            self.fields['store'].queryset = Store.objects.filter(id=request.user.store.id)
            self.fields['store'].initial = request.user.store

    def save(self, commit=True):
        user = super().save(commit=False)

        # Auto-assign permissions based on role
        role = user.role
        if role == 'admin':
            user.can_view_transfers = True
            user.can_adjust_stock = True
            user.can_transfer_stock = True
        elif role == 'manager':
            user.can_view_transfers = True
            user.can_transfer_stock = True
            user.can_adjust_stock = True
        elif role == 'clerk':
            user.can_adjust_stock = True
        elif role == 'staff':
            user.can_view_transfers = True
        elif role == 'sales':
            user.can_view_transfers = False
            user.can_adjust_stock = False
            user.can_transfer_stock = False

        if commit:
            user.save()
        return user
