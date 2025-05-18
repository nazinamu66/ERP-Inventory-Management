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
from xhtml2pdf import pisa




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
                messages.success(request, f"N{amount} deposited into {destination.name}.")
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
                messages.success(request, f"Payment of N{amount} recorded for {supplier.name}")
                return redirect('accounting:supplier_ledger', supplier_id=supplier.id)

            except Exception as e:
                messages.error(request, f"Transaction failed: {e}")
    else:
        form = SupplierPaymentForm()

    return render(request, 'accounting/record_supplier_payment.html', {'form': form})

from .models import ExpenseEntry  # 👈 Import the new model

from accounting.models import ExpenseEntry

from django.contrib.auth import get_user_model
from inventory.models import AuditLog
from inventory.models import Store

@login_required
def record_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense_account = form.cleaned_data['expense_account']
            payment_account = form.cleaned_data['payment_account']
            amount = form.cleaned_data['amount']
            date = form.cleaned_data['date']
            description = form.cleaned_data['description'] or f"Expense: {expense_account.name}"

            # Fallback store for users like admin with no assigned store
            store = getattr(request.user, 'store', None) or Store.objects.first()

            try:
                # Record transaction between accounts
                transaction = record_transaction_by_slug(
                    source_slug=payment_account.slug,
                    destination_slug=expense_account.slug,
                    amount=amount,
                    description=description,
                    store=store
                )

                # Create ExpenseEntry
                ExpenseEntry.objects.create(
                    expense_account=expense_account,
                    payment_account=payment_account,
                    amount=amount,
                    description=description,
                    date=date,
                    store=store,
                    user=request.user,
                    recorded_by=request.user
                )

                # 📝 Log to AuditLog
                AuditLog.objects.create(
                    user=request.user,
                    action='expense',
                    description=f"Recorded expense of N{amount} to '{expense_account.name}' from '{payment_account.name}'",
                    store=store
                )

                messages.success(request, f"✅ Expense of N{amount} recorded to {expense_account.name}")
                return redirect('accounting:account_ledger', slug=expense_account.slug)

            except Exception as e:
                messages.error(request, f"❌ Failed to record expense: {e}")
    else:
        form = ExpenseForm()

    return render(request, 'accounting/record_expense.html', {'form': form})


@login_required
def expense_history(request):
    user = request.user

    if user.role == 'admin':
        expenses = ExpenseEntry.objects.all()
    else:
        expenses = ExpenseEntry.objects.filter(store=user.store)

    if request.GET.get('account'):
        expenses = expenses.filter(expense_account__id=request.GET.get('account'))

    if request.GET.get('start_date'):
        expenses = expenses.filter(date__gte=request.GET.get('start_date'))

    if request.GET.get('end_date'):
        expenses = expenses.filter(date__lte=request.GET.get('end_date'))

    accounts = Account.objects.filter(type='expense')

    return render(request, 'accounting/expense_history.html', {
        'expenses': expenses.select_related('expense_account', 'payment_account', 'user'),
        'accounts': accounts,
    })

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

                messages.success(request, f"N{amount} transferred from {source.name} to {destination.name}.")
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
                messages.success(request, f"N{amount} withdrawn from {account.name}.")
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

from operator import itemgetter  # for sorting lists of dicts


@login_required
def customer_list_with_balances(request):
    query = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', '')

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

    # ✅ Sorting logic
    sort_map = {
        'balance_asc': ('balance', False),
        'balance_desc': ('balance', True),
        'invoiced_asc': ('invoiced', False),
        'invoiced_desc': ('invoiced', True),
        'paid_asc': ('paid', False),
        'paid_desc': ('paid', True),
    }

    if sort in sort_map:
        key, reverse = sort_map[sort]
        customer_data = sorted(customer_data, key=itemgetter(key), reverse=reverse)

    return render(request, 'accounting/customer_list.html', {
        'customers': customer_data,
        'query': query,
        'sort': sort,
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

            destination_slug = (
                payment.bank_account.slug if payment.payment_method == 'bank_transfer'
                else 'undeposited-funds'
            )

            txn = record_transaction_by_slug(
                source_slug='accounts-receivable',
                destination_slug=destination_slug,
                amount=payment.amount,
                description=description,
                store=request.user.store
            )

            payment.transaction = txn
            payment.save()

            if payment.invoice:
                sale = payment.invoice
                sale.amount_paid += payment.amount
                sale.save(update_fields=["amount_paid", "balance_due"])  # optionally update here
                sale.update_payment_status()
            else:
                # No invoice selected — optionally link manually or ignore
                pass

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
            sale_type='invoice'
        ).filter(total_amount__gt=F('amount_paid')).values(
            'id', 'receipt_number', 'total_amount', 'amount_paid'
        )

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

from datetime import date, timedelta, datetime
from django.db.models import F, ExpressionWrapper, DecimalField, Sum
from inventory.models import SaleItem, Sale
from accounting.models import ExpenseEntry

def get_profit_loss_context(start_date, end_date, store=None):
    # Filter sales by date and optionally by store
    sale_filter = {'sale_date__date__range': (start_date, end_date)}
    saleitem_filter = {'sale__sale_date__date__range': (start_date, end_date)}
    expense_filter = {'date__range': (start_date, end_date)}

    if store:
        sale_filter['store'] = store
        saleitem_filter['sale__store'] = store
        expense_filter['store'] = store

    # Revenue
    revenue = Sale.objects.filter(**sale_filter).aggregate(total=Sum('total_amount'))['total'] or 0

    # COGS
    cogs_qs = SaleItem.objects.filter(**saleitem_filter).annotate(
        cost=ExpressionWrapper(F('cost_price') * F('quantity'), output_field=DecimalField())
    )
    cogs = cogs_qs.aggregate(total=Sum('cost'))['total'] or 0

    # Expenses
    expenses = ExpenseEntry.objects.filter(**expense_filter).aggregate(total=Sum('amount'))['total'] or 0

    # Calculations
    gross_profit = revenue - cogs
    net_profit = gross_profit - expenses

    return {
        'start_date': start_date,
        'end_date': end_date,
        'revenue': revenue,
        'cogs': cogs,
        'gross_profit': gross_profit,
        'expenses': expenses,
        'net_profit': net_profit,
    }

from django.utils.timezone import now
# from datetime import date, timedelta, datetime


# ✅ Make it global
def parse_date_safe(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        try:
            return datetime.strptime(date_str, '%B %d, %Y').date()  # e.g., May 1, 2025
        except (ValueError, TypeError):
            return None


@login_required
def profit_loss_report(request):
    today = now().date()
    preset = request.GET.get('preset')
    store_id = request.GET.get('store')

    # Get selected store or default to user's assigned store
    store = Store.objects.filter(id=store_id).first() if store_id else getattr(request.user, 'store', None)

    # Handle Preset Filters
    if preset == 'this_month':
        start_date = date(today.year, today.month, 1)
        end_date = today
    elif preset == 'last_month':
        first_of_this_month = date(today.year, today.month, 1)
        last_month_end = first_of_this_month - timedelta(days=1)
        start_date = date(last_month_end.year, last_month_end.month, 1)
        end_date = last_month_end
    elif preset == 'this_year':
        start_date = date(today.year, 1, 1)
        end_date = today
    else:
        # Custom range from GET
        start = request.GET.get('start_date')
        end = request.GET.get('end_date')
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d").date() if start else date(today.year, today.month, 1)
            end_date = datetime.strptime(end, "%Y-%m-%d").date() if end else today
        except ValueError:
            start_date = date(today.year, today.month, 1)
            end_date = today

    # ✅ Only now do we call the profit/loss function
    context = get_profit_loss_context(start_date, end_date, store=store)

    # Add filter options to the context
    context['stores'] = Store.objects.all()
    context['selected_store_id'] = int(store_id) if store_id else None

    return render(request, 'accounting/profit_loss_report.html', context)

from django.http import HttpResponse
from django.template.loader import get_template

from inventory.models import CompanyProfile  # adjust to your actual path

@login_required
def profit_loss_pdf_view(request):
    raw_start = request.GET.get('start_date')
    raw_end = request.GET.get('end_date')
    store_id = request.GET.get('store')

    start_date = parse_date_safe(raw_start)
    end_date = parse_date_safe(raw_end)

    if not start_date or not end_date:
        messages.error(request, "Invalid date format. Use YYYY-MM-DD.")
        return redirect('accounting:profit_loss_report')

    store = None
    if store_id:
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            pass
    else:
        store = getattr(request.user, 'store', None)

    context = get_profit_loss_context(start_date, end_date, store)
    context.update({
        'request': request,
        'company': CompanyProfile.objects.first(),
        'store': store,
    })

    template = get_template('accounting/profit_loss_pdf.html')
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="profit_and_loss_report.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response


def parse_date_safe(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        try:
            return datetime.strptime(date_str, '%B %d, %Y').date()  # e.g., May 1, 2025
        except (ValueError, TypeError):
            return None


@login_required
def profit_loss_detail_report(request):
    today = now().date()
    preset = request.GET.get('preset')
    store_id = request.GET.get('store')

    # 🔁 Parse dates
    if preset == 'this_month':
        start_date = date(today.year, today.month, 1)
        end_date = today
    elif preset == 'last_month':
        first_of_this_month = date(today.year, today.month, 1)
        last_month_end = first_of_this_month - timedelta(days=1)
        start_date = date(last_month_end.year, last_month_end.month, 1)
        end_date = last_month_end
    elif preset == 'this_year':
        start_date = date(today.year, 1, 1)
        end_date = today
    else:
        start = request.GET.get('start_date')
        end = request.GET.get('end_date')
        start_date = parse_date_safe(start) or date(today.year, today.month, 1)
        end_date = parse_date_safe(end) or today

    # 🏬 Store filtering
    store = None
    if store_id:
        try:
            store = Store.objects.get(pk=store_id)
        except Store.DoesNotExist:
            store = None

    # 📦 Sales data
    sales_qs = SaleItem.objects.filter(sale__sale_date__date__range=(start_date, end_date))
    if store:
        sales_qs = sales_qs.filter(sale__store=store)

    sales_qs = (
        sales_qs
        .values('product__name')
        .annotate(
            quantity_sold=Sum('quantity'),
            total_sales=Sum(F('unit_price') * F('quantity'), output_field=DecimalField(max_digits=20, decimal_places=2)),
            total_cost=Sum(F('cost_price') * F('quantity'), output_field=DecimalField(max_digits=20, decimal_places=2)),
        )
        .order_by('product__name')
    )

    sales_data = []
    total_sales = total_cost = total_profit = 0

    for item in sales_qs:
        profit = item['total_sales'] - item['total_cost']
        sales_data.append({
            'product_name': item['product__name'],
            'quantity_sold': item['quantity_sold'],
            'total_sales': item['total_sales'],
            'total_cost': item['total_cost'],
            'profit': profit,
        })
        total_sales += item['total_sales'] or 0
        total_cost += item['total_cost'] or 0
        total_profit += profit or 0

    # 💸 Expenses data
    expenses_qs = ExpenseEntry.objects.filter(date__range=(start_date, end_date))
    if store:
        expenses_qs = expenses_qs.filter(store=store)

    expenses_qs = (
        expenses_qs
        .values('expense_account__name')
        .annotate(total_expense=Sum('amount'))
        .order_by('expense_account__name')
    )

    total_expenses = 0
    expense_data = []
    for exp in expenses_qs:
        expense_data.append({
            'category': exp['expense_account__name'],
            'amount': exp['total_expense'],
        })
        total_expenses += exp['total_expense'] or 0

    # 🧮 Calculations
    gross_profit = total_sales - total_cost
    net_profit = gross_profit - total_expenses

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'sales_data': sales_data,
        'expense_data': expense_data,
        'stores': Store.objects.all(),
        'selected_store_id': int(store_id) if store_id else None,
        'totals': {
            'total_sales': total_sales,
            'total_cost': total_cost,
            'gross_profit': gross_profit,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
        }
    }

    return render(request, 'accounting/profit_loss_detail_report.html', context)

@login_required
def profit_loss_detail_pdf_view(request):
    start = request.GET.get('start_date')
    end = request.GET.get('end_date')
    store_id = request.GET.get('store')

    start_date = parse_date_safe(start)
    end_date = parse_date_safe(end)

    if not start_date or not end_date:
        return HttpResponse("Invalid dates provided", status=400)

    store = get_object_or_404(Store, pk=store_id) if store_id else None

    sales_qs = SaleItem.objects.filter(sale__sale_date__date__range=(start_date, end_date))
    if store:
        sales_qs = sales_qs.filter(sale__store=store)

    # Annotate basic values (no Sum on expression)
    sales_qs = (
        sales_qs
        .values('product__name', 'unit_price', 'cost_price')
        .annotate(quantity=Sum('quantity'))
        .order_by('product__name')
    )

    items = []
    total_quantity = total_sales = total_cost = total_profit = 0

    for item in sales_qs:
        unit_price = item['unit_price'] or 0
        cost_price = item['cost_price'] or 0
        quantity = item['quantity'] or 0
        total_sale = unit_price * quantity
        total_cogs = cost_price * quantity
        profit = total_sale - total_cogs

        items.append({
            'product_name': item['product__name'],
            'unit_price': unit_price,
            'cost_price': cost_price,
            'quantity': quantity,
            'total_sales': total_sale,
            'total_cost': total_cogs,
            'profit': profit,
        })

        total_quantity += quantity
        total_sales += total_sale
        total_cost += total_cogs
        total_profit += profit

    # Expenses
    expense_qs = ExpenseEntry.objects.filter(date__range=(start_date, end_date))
    if store:
        expense_qs = expense_qs.filter(store=store)

    expense_data = []
    total_expenses = 0

    for e in expense_qs.values('expense_account__name').annotate(total=Sum('amount')):
        expense_data.append({
            'category': e['expense_account__name'],
            'amount': e['total'] or 0
        })
        total_expenses += e['total'] or 0

    gross_profit = total_sales - total_cost
    net_profit = gross_profit - total_expenses

    context = {
        'items': items,
        'expense_data': expense_data,
        'total_quantity': total_quantity,
        'total_sales': total_sales,
        'total_cost': total_cost,
        'total_profit': total_profit,
        'totals': {
            'gross_profit': gross_profit,
            'net_profit': net_profit,
            'total_expenses': total_expenses,
        },
        'start_date': start_date,
        'end_date': end_date,
        'company': CompanyProfile.objects.first(),
        'now': now(),
        'request': request,
    }

    template = get_template('accounting/profit_loss_detail_pdf.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="profit_loss_detail_report.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response
