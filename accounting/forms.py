# accounting/forms.py

from django import forms
from .models import CustomerPayment
from inventory.models import Customer, Sale  # 👈 include Sale
from accounting.models import Account

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
