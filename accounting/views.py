from decimal import Decimal
from itertools import chain
from datetime import datetime, timedelta
import accounting.models as accounting_models 

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone

from weasyprint import HTML

from .forms import CustomerPaymentForm
from .models import CustomerPayment, Account, TransactionLine, SupplierPayment
from .services import calculate_account_balances, record_transaction_by_slug
from inventory.models import Customer, Sale
from inventory.models import CompanyProfile  # adjust if path differs
from accounting.models import SupplierLedger
from inventory.models import Supplier
from inventory.models import Purchase
from .forms import SupplierPaymentForm, AccountTransferForm
from .forms import WithdrawForm
from .forms import AccountDepositForm
from .forms import ExpenseForm
from django.views.decorators.http import require_POST
from inventory.forms import CustomerForm





@login_required
def record_account_deposit(request):
    if request.method == 'POST':
        form = AccountDepositForm(request.POST)
        if form.is_valid():
            destination = form.cleaned_data['destination_account']
            amount = form.cleaned_data['amount']
            note = form.cleaned_data['note'] or f"Deposit to {destination.name}"

            try:
                transaction = record_transaction_by_slug(
                    destination_slug=destination.slug,
                    amount=amount,
                    description=note,
                    is_deposit=True,
                    store=request.user.store  # ← required!

                )
                messages.success(request, f"₹{amount} deposited into {destination.name}.")
                return redirect('accounting:account_ledger', slug=destination.slug)
            except Exception as e:
                messages.error(request, f"Deposit failed: {e}")
    else:
        form = AccountDepositForm()

    return render(request, 'accounting/record_account_deposit.html', {'form': form})


@login_required
def record_supplier_payment(request):
    if request.method == 'POST':
        form = SupplierPaymentForm(request.POST)
        if form.is_valid():
            supplier = form.cleaned_data['supplier']
            account = form.cleaned_data['account']
            amount = form.cleaned_data['amount']
            payment_date = form.cleaned_data['payment_date']
            note = form.cleaned_data['note']

            try:
                # 1. Record transaction — this should also handle SupplierLedger
                transaction = record_transaction_by_slug(
                    source_slug=account.slug,
                    destination_slug="accounts-payable",  # supplier control account
                    amount=amount,
                    description=note or f"Payment to {supplier.name}",
                    supplier=supplier,
                    store=request.user.store  # ← required!

                )

                # 3. Redirect to correct ledger URL name
                messages.success(request, f"Payment of ₹{amount} recorded for {supplier.name}")
                return redirect('accounting:supplier_ledger', supplier_id=supplier.id)

            except Exception as e:
                messages.error(request, f"Transaction failed: {e}")
    else:
        form = SupplierPaymentForm()

    return render(request, 'accounting/record_supplier_payment.html', {'form': form})

@login_required
def record_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense_account = form.cleaned_data['expense_account']
            payment_account = form.cleaned_data['payment_account']
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description'] or f"Expense: {expense_account.name}"

            try:
                transaction = record_transaction_by_slug(
                    source_slug=payment_account.slug,
                    destination_slug=expense_account.slug,
                    amount=amount,
                    description=description,
                    store=request.user.store  # ← required!

                )

                messages.success(request, f"Expense of ₹{amount} recorded to {expense_account.name}")
                return redirect('accounting:account_ledger', slug=expense_account.slug)

            except Exception as e:
                messages.error(request, f"Failed to record expense: {e}")
    else:
        form = ExpenseForm()

    return render(request, 'accounting/record_expense.html', {'form': form})


# views.py
@login_required
def record_account_transfer(request):
    if request.method == 'POST':
        form = AccountTransferForm(request.POST)
        if form.is_valid():
            source = form.cleaned_data['source_account']
            destination = form.cleaned_data['destination_account']
            amount = form.cleaned_data['amount']
            note = form.cleaned_data['note'] or f"Transfer from {source.name} to {destination.name}"

            try:
                # Reuse your central transaction logic
                transaction = record_transaction_by_slug(
                    source_slug=source.slug,
                    destination_slug=destination.slug,
                    amount=amount,
                    description=note,
                    store=request.user.store  # ← required!

                )

                messages.success(request, f"₹{amount} transferred from {source.name} to {destination.name}.")
                return redirect('accounting:account_ledger', slug=source.slug)

            except Exception as e:
                messages.error(request, f"Transfer failed: {e}")
    else:
        form = AccountTransferForm()

    return render(request, 'accounting/record_account_transfer.html', {'form': form})

@login_required
def withdraw_funds(request):
    if request.method == 'POST':
        form = WithdrawForm(request.POST)
        if form.is_valid():
            account = form.cleaned_data['account']
            amount = form.cleaned_data['amount']
            note = form.cleaned_data['note'] or f"Withdrawal from {account.name}"

            try:
                record_transaction_by_slug(
                    source_slug=account.slug,
                    destination_slug=None,  # Not needed for withdrawal
                    amount=amount,
                    description=note,
                    is_withdrawal=True,  # Add this flag in your util
                    store=request.user.store  # ← required!

                )
                messages.success(request, f"₹{amount} withdrawn from {account.name}.")
                return redirect('accounting:account_ledger', slug=account.slug)
            except Exception as e:
                messages.error(request, f"Withdrawal failed: {e}")
    else:
        form = WithdrawForm()

    return render(request, 'accounting/withdraw_funds.html', {'form': form})

@login_required
def supplier_balances(request):
    if not request.user.is_superuser and request.user.role != 'manager':
        messages.error(request, "Not authorized.")
        return render(request, 'errors/permission_denied.html', status=403)

    suppliers = Supplier.objects.all()
    supplier_data = []

    for supplier in suppliers:
        total_invoiced = Purchase.objects.filter(supplier=supplier).aggregate(total=Sum('total_amount'))['total'] or 0
        total_paid = SupplierPayment.objects.filter(supplier=supplier).aggregate(total=Sum('amount'))['total'] or 0
        balance = total_invoiced - total_paid

        supplier_data.append({
            'supplier': supplier,
            'invoiced': total_invoiced,
            'paid': total_paid,
            'balance': balance
        })

    return render(request, 'dashboard/supplier_balances.html', {'suppliers': supplier_data})

@login_required
def supplier_ledger_view(request, supplier_id):
    if not request.user.is_superuser and request.user.role != 'manager':
        messages.error(request, "Not authorized.")
        return render(request, 'errors/permission_denied.html', status=403)

    supplier = get_object_or_404(Supplier, id=supplier_id)
    ledger_entries = SupplierLedger.objects.filter(supplier=supplier).select_related('transaction').order_by('transaction__created_at')

    balance = 0
    ledger = []

    for entry in ledger_entries:
        # 🧾 For supplier ledger: DEBIT = reduce balance (payment), CREDIT = increase balance (purchase)
        amount = entry.amount if entry.entry_type == 'credit' else -entry.amount
        balance += amount
        ledger.append({
            'date': entry.transaction.created_at,
            'type': entry.get_entry_type_display(),
            'amount': amount,
            'balance': balance,
            'note': entry.transaction.description or ''
        })
    context = {
        'supplier': supplier,
        'ledger': ledger,
        'final_balance': balance
    }
    return render(request, 'dashboard/supplier_ledger.html', context)


def parse_date_with_tz(date_str, end_of_day=False):
    """Parses a YYYY-MM-DD string and returns a timezone-aware datetime."""
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        if end_of_day:
            date += timedelta(days=1)
        return timezone.make_aware(date)
    except Exception:
        return None


def build_customer_ledger(customer, from_date_str=None, to_date_str=None):
    from_date = parse_date_with_tz(from_date_str)
    to_date = parse_date_with_tz(to_date_str, end_of_day=True)

    invoices = Sale.objects.filter(customer=customer, sale_type='invoice')
    payments = CustomerPayment.objects.filter(customer=customer)

    if from_date:
        invoices = invoices.filter(sale_date__gte=from_date)
        payments = payments.filter(created_at__gte=from_date)
    if to_date:
        invoices = invoices.filter(sale_date__lt=to_date)
        payments = payments.filter(created_at__lt=to_date)

    invoices = invoices.annotate(entry_type=Value('Invoice'), entry_amount=F('total_amount'), date=F('sale_date'))
    payments = payments.annotate(entry_type=Value('Payment'), entry_amount=F('amount'), date=F('created_at'))

    transactions = sorted(chain(invoices, payments), key=lambda x: x.date)

    running_balance = Decimal('0.00')
    ledger = []

    for tx in transactions:
        running_balance += tx.entry_amount if tx.entry_type == 'Invoice' else -tx.entry_amount
        ledger.append({
            'date': tx.date,
            'type': tx.entry_type,
            'amount': tx.entry_amount,
            'balance': running_balance,
            'note': getattr(tx, 'remarks', '') or getattr(tx, 'note', '')
        })

    return ledger, running_balance



from django.db.models import Q

@login_required
def customer_list_with_balances(request):
    query = request.GET.get('q', '')
    customers = Customer.objects.all()

    if query:
        customers = customers.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )

    customer_data = []

    for customer in customers:
        total_invoiced = Sale.objects.filter(customer=customer, sale_type='invoice') \
            .aggregate(total=Coalesce(Sum('total_amount'), Decimal('0.00')))['total']

        total_paid = CustomerPayment.objects.filter(customer=customer) \
            .aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']

        balance = Decimal(total_invoiced) - Decimal(total_paid)

        customer_data.append({
            'customer': customer,
            'invoiced': total_invoiced,
            'paid': total_paid,
            'balance': balance
        })

    return render(request, 'accounting/customer_list.html', {
        'customers': customer_data,
        'query': query,
    })


@login_required
def customer_ledger_view(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)
    from_date = request.GET.get('from')
    to_date = request.GET.get('to')
    transaction_type = request.GET.get('type')  # e.g. 'Invoice', 'Payment'
    

    ledger, running_balance = build_customer_ledger(customer, from_date, to_date)

    if transaction_type:
        ledger = [entry for entry in ledger if entry['type'].lower() == transaction_type.lower()]

    return render(request, 'accounting/customer_ledger.html', {
        'customer': customer,
        'ledger': ledger,
        'from': from_date,
        'to': to_date,
        'type': transaction_type,
        'final_balance': running_balance
    })


@login_required
def customer_ledger_pdf(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)
    from_date = request.GET.get('from')
    to_date = request.GET.get('to')
    transaction_type = request.GET.get('type')  # ✅ get the filter from query params
    company = CompanyProfile.objects.first()

    ledger, running_balance = build_customer_ledger(customer, from_date, to_date)

    if transaction_type:
        ledger = [entry for entry in ledger if entry['type'].lower() == transaction_type.lower()]
        # Optionally recalculate running balance (if shown in PDF)
        balance = Decimal('0.00')
        for entry in ledger:
            if entry['type'] == 'Invoice':
                balance += entry['amount']
            else:
                balance -= entry['amount']
        running_balance = balance

    html_string = render_to_string('pdf/customer_ledger_pdf.html', {
        'customer': customer,
        'ledger': ledger,
        'final_balance': running_balance,
        'from': from_date,
        'to': to_date,
        'type': transaction_type,  # ✅ Pass to template (optional)
        'company': company,
    })

    pdf_file = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename=ledger_{customer.id}.pdf'
    return response

@login_required
def edit_customer(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer details updated successfully.')
            return redirect('accounting:customer_list')
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'accounting/edit_customer.html', {'form': form, 'customer': customer})


@login_required
@require_POST
def delete_customer(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)
    customer_name = customer.name
    customer.delete()
    messages.success(request, f"Customer '{customer_name}' deleted successfully.")
    return redirect('accounting:customer_list')


# from django.db.models import Q

@login_required
def account_ledger_view(request, slug):
    account = get_object_or_404(Account, slug=slug)
    user = request.user

    # For managers, assume `user.store` gives their assigned store
    user_store = getattr(user, 'store', None)

    # Filter transaction lines based on store
    transaction_lines = TransactionLine.objects.filter(account=account)

    if user_store:
        # Only include lines where the transaction belongs to the manager's store
        transaction_lines = transaction_lines.filter(transaction__store=user_store)

    transaction_lines = transaction_lines.select_related('transaction') \
        .order_by('transaction__created_at', 'id')

    balance = Decimal(account.opening_balance or 0)
    history = []

    for line in transaction_lines:
        balance += Decimal(line.debit or 0) - Decimal(line.credit or 0)
        history.append({
            'date': line.transaction.created_at,
            'description': line.transaction.description,
            'debit': line.debit,
            'credit': line.credit,
            'balance': balance
        })

    return render(request, 'accounting/account_ledger.html', {
        'account': account,
        'history': history,
    })



@login_required
def receive_customer_payment(request):
    if request.method == 'POST':
        form = CustomerPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            description = f"Payment from {payment.customer.name}"

            txn = record_transaction_by_slug(
                source_slug='accounts-receivable',
                destination_slug=payment.bank_account.slug if payment.payment_method == 'bank_transfer' else 'undeposited-funds',
                amount=payment.amount,
                description=description,
                store=request.user.store  # ← required!

            )

            payment.transaction = txn
            payment.save()

            if payment.invoice:
                sale = payment.invoice
                sale.amount_paid += payment.amount
                sale.update_payment_status()

            messages.success(request, f"Received payment from {payment.customer.name}")
            return redirect('accounting:receive_customer_payment')
    else:
        form = CustomerPaymentForm()

    return render(request, 'accounting/receive_payment.html', {'form': form})


@login_required
def get_unpaid_invoices(request):
    customer_id = request.GET.get('customer_id')
    invoices = []
    if customer_id:
        invoices = Sale.objects.filter(
            customer_id=customer_id,
            sale_type='invoice',
            payment_status='unpaid'
        ).values('id', 'invoice_number', 'total_amount', 'amount_paid')

    return JsonResponse(list(invoices), safe=False)

@login_required
def account_balances_view(request):
    user = request.user

    # Admins see all; Managers see their store’s data only
    if user.role == 'manager' and user.store:
        balances = calculate_account_balances(store=user.store)
    else:
        balances = calculate_account_balances()

    return render(request, 'accounting/account_balances.html', {
        'balances': balances
    })



