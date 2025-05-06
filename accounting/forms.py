# accounting/forms.py

from django import forms
from .models import CustomerPayment
from inventory.models import Customer, Sale  # 👈 include Sale
from accounting.models import Account
from inventory.models import Supplier


class ExpenseForm(forms.Form):
    expense_account = forms.ModelChoiceField(queryset=Account.objects.none(), label="Expense Category")
    payment_account = forms.ModelChoiceField(queryset=Account.objects.none(), label="Paid From")
    amount = forms.DecimalField(decimal_places=2)
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    description = forms.CharField(required=False, widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['expense_account'].queryset = Account.objects.filter(type__iexact='expense')
        self.fields['payment_account'].queryset = Account.objects.filter(type__in=['bank', 'asset'])


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

        # Dynamically set available invoices if customer is already selected
        if 'customer' in self.data:
            try:
                customer_id = int(self.data.get('customer'))
                self.fields['invoice'].queryset = Sale.objects.filter(
                    customer_id=customer_id,
                    sale_type='invoice',
                    payment_status='unpaid'
                )
            except (ValueError, TypeError):
                pass  # invalid input from the form
        elif self.instance.pk and self.instance.customer:
            self.fields['invoice'].queryset = Sale.objects.filter(
                customer=self.instance.customer,
                sale_type='invoice',
                payment_status='unpaid'
            )
