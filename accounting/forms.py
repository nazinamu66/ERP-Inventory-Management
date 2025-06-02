# accounting/forms.py

from django import forms
from .models import CustomerPayment
from inventory.models import Customer, Sale, PurchaseOrder # 👈 include Sale
from accounting.models import Account
from inventory.models import Supplier
from django.db.models import F



# accounting/forms.py

from django import forms
from inventory.models import PurchaseOrder, Store
from accounting.models import Account, ExpenseEntry

class ExpenseForm(forms.Form):
    expense_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(type__iexact='expense'),
        label="Expense Category"
    )

    payment_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(type__in=['bank', 'asset']),
        label="Paid From"
    )

    amount = forms.DecimalField(decimal_places=2, max_digits=12)
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional notes'})
    )

    purchase_orders = forms.ModelMultipleChoiceField(
        queryset=PurchaseOrder.objects.none(),
        required=False,
        label="Linked Purchase Orders",
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Dynamically filter purchase orders
        if user:
            if user.is_superuser or user.role == 'admin':
                self.fields['purchase_orders'].queryset = PurchaseOrder.objects.filter(status='received')
            else:
                store = getattr(user, 'store', None)
                if store:
                    self.fields['purchase_orders'].queryset = PurchaseOrder.objects.filter(store=store, status='received')
                else:
                    self.fields['purchase_orders'].queryset = PurchaseOrder.objects.none()

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.fields['expense_account'].queryset = Account.objects.filter(type__iexact='expense')
    #     self.fields['payment_account'].queryset = Account.objects.filter(type__in=['bank', 'asset'])


class AccountDepositForm(forms.Form):
    destination_account = forms.ModelChoiceField(queryset=Account.objects.all())
    amount = forms.DecimalField(max_digits=12, decimal_places=2)
    note = forms.CharField(required=False)


class WithdrawForm(forms.Form):
    account = forms.ModelChoiceField(queryset=Account.objects.all(), label="Withdraw From")
    amount = forms.DecimalField(max_digits=12, decimal_places=2)
    note = forms.CharField(widget=forms.Textarea, required=False)



class AccountTransferForm(forms.Form):
    source_account = forms.ModelChoiceField(
        queryset=Account.objects.all(), label="Transfer From"
    )
    destination_account = forms.ModelChoiceField(
        queryset=Account.objects.all(), label="Transfer To"
    )
    amount = forms.DecimalField(decimal_places=2, max_digits=10)
    transfer_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    note = forms.CharField(widget=forms.Textarea, required=False)

    def clean(self):
        cleaned = super().clean()
        source = cleaned.get('source_account')
        dest = cleaned.get('destination_account')
        if source and dest and source == dest:
            raise forms.ValidationError("Source and destination cannot be the same.")
        return cleaned

from inventory.models import Store

class GeneralLedgerForm(forms.Form):
    account = forms.ModelChoiceField(queryset=Account.objects.all(), label="Account")
    store = forms.ModelChoiceField(queryset=Store.objects.none(), required=False, label="Store")
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if request:
            user = request.user
            if user.is_superuser or user.role == 'admin':
                self.fields['store'].queryset = Store.objects.all()
            else:
                self.fields['store'].queryset = user.stores.all()

class SupplierPaymentForm(forms.Form):
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.all(), required=True)
    account = forms.ModelChoiceField(
        queryset=Account.objects.filter(type__in=['bank', 'cash']),
        required=True,
        label="Paid From (Cash/Bank)"
    )
    amount = forms.DecimalField(decimal_places=2, max_digits=10, required=True)
    payment_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)
    note = forms.CharField(widget=forms.Textarea, required=False)




class CustomerPaymentForm(forms.ModelForm):
    invoice = forms.ModelChoiceField(
        queryset=Sale.objects.none(), required=False, label="Invoice",
        help_text="Optional. Link this payment to a specific invoice."
    )

    class Meta:
        model = CustomerPayment
        fields = ['customer', 'invoice', 'amount', 'payment_method', 'bank_account', 'remarks']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['bank_account'].queryset = Account.objects.filter(type='asset')

        if 'customer' in self.data:
            try:
                customer_id = int(self.data.get('customer'))
                self.fields['invoice'].queryset = Sale.objects.filter(
                    customer_id=customer_id,
                    sale_type='invoice'
                ).filter(total_amount__gt=F('amount_paid'))
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.customer:
            self.fields['invoice'].queryset = Sale.objects.filter(
                customer=self.instance.customer,
                sale_type='invoice'
            ).filter(total_amount__gt=F('amount_paid'))
    
    def clean(self):
        cleaned_data = super().clean()
        invoice = cleaned_data.get("invoice")
        amount = cleaned_data.get("amount")

        if invoice and amount:
            balance = invoice.total_amount - invoice.amount_paid
            if amount > balance:
                self.add_error('amount', f"Payment exceeds balance. Remaining: ₦{balance:.2f}")

