from django import forms
from users.models import User
from inventory.models import Store

class UserForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'role', 'stores',  # use 'stores' not 'store'
            'is_active', 'can_view_transfers',
            'can_adjust_stock', 'can_transfer_stock',
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'stores': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(),
            'can_view_transfers': forms.CheckboxInput(),
            'can_adjust_stock': forms.CheckboxInput(),
            'can_transfer_stock': forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if request and request.user.role == 'manager':
            self.fields['role'].choices = [
                ('staff', 'Store Staff'),
                ('clerk', 'Inventory Clerk'),
                ('sales', 'Sales Staff'),
            ]
            self.fields['stores'].queryset = Store.objects.filter(id=request.user.store.id)
            self.fields['stores'].initial = [request.user.store]

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')

        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError("Passwords do not match.")
            if len(p1) < 6:
                raise forms.ValidationError("Password must be at least 6 characters.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        # Auto-permissions
        role = user.role
        if role == 'admin':
            user.can_view_transfers = user.can_adjust_stock = user.can_transfer_stock = True
        elif role == 'manager':
            user.can_view_transfers = user.can_transfer_stock = user.can_adjust_stock = True
        elif role == 'clerk':
            user.can_adjust_stock = True
        elif role == 'staff':
            user.can_view_transfers = True
        elif role == 'sales':
            user.can_view_transfers = user.can_adjust_stock = user.can_transfer_stock = False

        # Password
        password = self.cleaned_data.get('password1')
        if password:
            user.set_password(password)
        elif not user.pk:  # New user without password
            user.set_password('changeme')

        if commit:
            user.save()
            self.save_m2m()
        return user
