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

from django.template.loader import get_template
from inventory.models import CompanyProfile  
from django.db.models import Q
from operator import itemgetter


from datetime import date
from django.db.models import ExpressionWrapper, DecimalField
from inventory.models import SaleItem
from accounting.models import ExpenseEntry
from .forms import GeneralLedgerForm



def get_user_allowed_store(request, store_id):
    """
    Restricts access to the requested store unless user is admin/superuser.
    Falls back to first assigned store or None.
    """
    user = request.user
    if user.is_superuser or user.role == 'admin':
        return Store.objects.filter(id=store_id).first() if store_id else None

    user_store_ids = user.stores.values_list('id', flat=True)
    if store_id and int(store_id) in user_store_ids:
        return Store.objects.filter(id=store_id).first()
    return user.stores.first()



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
                    store = request.user.get_active_store(request)

                )
                messages.success(request, f"N{amount} deposited into {destination.name}.")
                return redirect('accounting:account_ledger', slug=destination.slug)
            except Exception as e:
                messages.error(request, f"Deposit failed: {e}")
    else:
        form = AccountDepositForm()

    return render(request, 'accounting/record_account_deposit.html', {'form': form})



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
                    store = request.user.get_active_store(request)

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
                    store = request.user.get_active_store(request)

                )
                messages.success(request, f"N{amount} withdrawn from {account.name}.")
                return redirect('accounting:account_ledger', slug=account.slug)
            except Exception as e:
                messages.error(request, f"Withdrawal failed: {e}")
    else:
        form = WithdrawForm()

    return render(request, 'accounting/withdraw_funds.html', {'form': form})



from collections import defaultdict

# from collections import defaultdict
# from django.shortcuts import render
# from django.utils.timezone import now
from inventory.models import Sale
# from django.contrib.auth.decorators import login_required

@login_required
def customer_aging_report_view(request):
    today = now().date()
    search = request.GET.get('q', '').strip()
    bucket_filter = request.GET.get('bucket')

    invoices = (
        Sale.objects
        .filter(sale_type='invoice')
        .exclude(balance_due=0)
        .select_related('customer')
    )

    if search:
        invoices = invoices.filter(
            Q(customer__name__icontains=search) |
            Q(customer__email__icontains=search)
        )

    grouped = defaultdict(lambda: defaultdict(list))

    for invoice in invoices:
        if not invoice.customer:
            continue

        age = (today - invoice.sale_date.date()).days
        if age <= 30:
            bucket = '0–30 days'
        elif age <= 60:
            bucket = '31–60 days'
        elif age <= 90:
            bucket = '61–90 days'
        else:
            bucket = '90+ days'

        paid = invoice.amount_paid or 0
        total = invoice.total_amount or 0
        balance = total - paid
        if balance <= 0:
            continue

        # ❗ Skip if user filtered a different bucket
        if bucket_filter and bucket_filter != bucket:
            continue

        grouped[invoice.customer][bucket].append({
            'invoice': invoice,
            'amount': total,
            'paid': paid,
            'balance': balance,
            'bucket': bucket,
            'due_days': age,
            'date': invoice.sale_date.date(),
        })

    for customer in grouped:
        grouped[customer] = dict(grouped[customer])

    return render(request, 'accounting/customer_aging_report.html', {
        'grouped': dict(grouped),
        'today': today,
        'search': search,
        'bucket_filter': bucket_filter,
    })

# from django.template.loader import render_to_string
# from weasyprint import HTML

# from inventory.models import CompanyProfile  # Adjust path if needed

@login_required
def customer_aging_report_pdf(request):
    today = now().date()
    search = request.GET.get('q', '').strip()
    bucket_filter = request.GET.get('bucket')
    company = CompanyProfile.objects.first()

    invoices = (
        Sale.objects
        .filter(sale_type='invoice')
        .exclude(balance_due=0)
        .select_related('customer')
    )

    if search:
        invoices = invoices.filter(
            Q(customer__name__icontains=search) |
            Q(customer__email__icontains=search)
        )

    grouped = defaultdict(lambda: defaultdict(list))

    for invoice in invoices:
        if not invoice.customer:
            continue

        age = (today - invoice.sale_date.date()).days
        if age <= 30:
            bucket = '0–30 days'
        elif age <= 60:
            bucket = '31–60 days'
        elif age <= 90:
            bucket = '61–90 days'
        else:
            bucket = '90+ days'

        paid = invoice.amount_paid or 0
        total = invoice.total_amount or 0
        balance = total - paid
        if balance <= 0:
            continue

        if bucket_filter and bucket_filter != bucket:
            continue

        grouped[invoice.customer][bucket].append({
            'invoice': invoice,
            'amount': total,
            'paid': paid,
            'balance': balance,
            'bucket': bucket,
            'due_days': age,
            'date': invoice.sale_date.date(),
        })

    for customer in grouped:
        grouped[customer] = dict(grouped[customer])

    html = render_to_string('pdf/customer_aging_report_pdf.html', {
        'grouped': dict(grouped),
        'today': today,
        'company': company,
    })

    pdf_file = HTML(string=html).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="customer_aging_report.pdf"'
    return response



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
                # 1️⃣ Record the transaction
                txn = record_transaction_by_slug(
                    source_slug=account.slug,
                    destination_slug="accounts-payable",
                    amount=amount,
                    description=note or f"Payment to {supplier.name}",
                    supplier=supplier,
                    store=request.user.get_active_store(request)
                )

                # 2️⃣ Create and link SupplierPayment
                SupplierPayment.objects.create(
                    supplier=supplier,
                    account=account,
                    amount=amount,
                    payment_date=payment_date,
                    note=note,
                    created_by=request.user,
                    transaction=txn
                )

                messages.success(request, f"Payment of ₦{amount} recorded for {supplier.name}")
                return redirect('accounting:supplier_ledger', supplier_id=supplier.id)

            except Exception as e:
                messages.error(request, f"Transaction failed: {e}")
    else:
        form = SupplierPaymentForm()

    return render(request, 'accounting/record_supplier_payment.html', {'form': form})


from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from decimal import Decimal
from inventory.models import PurchaseOrderItem

@login_required
def supplier_balances(request):
    if not request.user.is_superuser and request.user.role != 'manager':
        messages.error(request, "Not authorized.")
        return render(request, 'errors/permission_denied.html', status=403)

    suppliers = Supplier.objects.all()
    store_filter = None

    # 🔒 For managers, restrict based on allowed stores
    if request.user.role == 'manager':
        store_ids = request.user.stores.values_list('id', flat=True)
        store_filter = Q(purchase_order__store__in=store_ids)

    supplier_data = []

    for supplier in suppliers:
        # 📦 Total invoiced: sum of all PO item subtotals
        po_items = PurchaseOrderItem.objects.filter(purchase_order__supplier=supplier)
        if store_filter:
            po_items = po_items.filter(store_filter)

        total_invoiced = po_items.aggregate(
            total=Sum(F('quantity') * F('unit_price'), output_field=DecimalField())
        )['total'] or Decimal('0.00')

        # 💸 Total paid
        payments = SupplierPayment.objects.filter(supplier=supplier)
        if store_filter:
            payments = payments.filter(transaction__store__in=store_ids)

        total_paid = payments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        balance = total_invoiced - total_paid

        supplier_data.append({
            'supplier': supplier,
            'invoiced': total_invoiced,
            'paid': total_paid,
            'balance': balance
        })

    return render(request, 'dashboard/supplier_balances.html', {
        'suppliers': supplier_data
    })


@login_required
def supplier_ledger_view(request, supplier_id):
    if not request.user.is_superuser and request.user.role != 'manager':
        messages.error(request, "Not authorized.")
        return render(request, 'errors/permission_denied.html', status=403)

    supplier = get_object_or_404(Supplier, id=supplier_id)

    # ✅ Date filters
    from_date_str = request.GET.get('from')
    to_date_str = request.GET.get('to')

    from_date = parse_date_with_tz(from_date_str)
    to_date = parse_date_with_tz(to_date_str, end_of_day=True)

    # 🔁 Get entries
    ledger_qs = SupplierLedger.objects.filter(supplier=supplier).select_related('transaction').order_by('transaction__created_at')

    if from_date:
        ledger_qs = ledger_qs.filter(transaction__created_at__gte=from_date)
    if to_date:
        ledger_qs = ledger_qs.filter(transaction__created_at__lte=to_date)

    # 🧮 Running balance
    balance = 0
    ledger = []
    for entry in ledger_qs:
        amount = entry.amount if entry.entry_type == 'credit' else -entry.amount
        balance += amount
        ledger.append({
            'date': entry.transaction.created_at,
            'type': entry.get_entry_type_display(),
            'amount': amount,
            'balance': balance,
            'note': entry.transaction.description or ''
        })

    return render(request, 'dashboard/supplier_ledger.html', {
        'supplier': supplier,
        'ledger': ledger,
        'final_balance': balance,
        'from': from_date_str,
        'to': to_date_str,
    })


def parse_date_with_tz(date_str, end_of_day=False):
    """Parses a YYYY-MM-DD string and returns a timezone-aware datetime."""
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        if end_of_day:
            date += timedelta(days=1)
        return timezone.make_aware(date)
    except Exception:
        return None
    
from django.template.loader import render_to_string
from weasyprint import HTML

@login_required
def supplier_ledger_pdf(request, supplier_id):
    supplier = get_object_or_404(Supplier, pk=supplier_id)
    from_date = request.GET.get('from')
    to_date = request.GET.get('to')
    company = CompanyProfile.objects.first()

    entries = SupplierLedger.objects.filter(supplier=supplier).select_related('transaction').order_by('transaction__created_at')

    # Filter by date range
    if from_date:
        entries = entries.filter(transaction__created_at__date__gte=from_date)
    if to_date:
        entries = entries.filter(transaction__created_at__date__lte=to_date)

    balance = Decimal('0.00')
    ledger = []
    for entry in entries:
        amount = entry.amount if entry.entry_type == 'credit' else -entry.amount
        balance += amount
        ledger.append({
            'date': entry.transaction.created_at,
            'type': entry.get_entry_type_display(),
            'amount': amount,
            'balance': balance,
            'note': entry.transaction.description or ''
        })

    html_string = render_to_string('pdf/supplier_ledger_pdf.html', {
        'supplier': supplier,
        'ledger': ledger,
        'final_balance': balance,
        'from': from_date,
        'to': to_date,
        'company': company,
    })

    pdf_file = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename=supplier_ledger_{supplier.id}.pdf'
    return response




@login_required
def balance_sheet_view(request):
    user = request.user
    store_id = request.GET.get('store')
    as_of_date = parse_date_safe(request.GET.get('date')) or now().date()

    if user.is_superuser or user.role == 'admin':
        store_qs = Store.objects.all()
        store = Store.objects.filter(id=store_id).first() if store_id else None
    else:
        store_qs = user.stores.all()
        store = user.stores.filter(id=store_id).first() if store_id else user.stores.first()

    if not store:
        messages.error(request, "No valid store selected.")
        return redirect('dashboard')

    # 🔎 Pull account balances from TransactionLines
    lines = (
        TransactionLine.objects
        .filter(transaction__store=store, transaction__created_at__date__lte=as_of_date)
        .values('account__name', 'account__type')
        .annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )
        .order_by('account__name')
    )

    assets, liabilities, equity = [], [], []
    totals = {'asset': 0, 'liability': 0, 'equity': 0}

    for line in lines:
        acc_type = line['account__type']
        name = line['account__name']
        debit = line['total_debit'] or 0
        credit = line['total_credit'] or 0
        balance = debit - credit

        if acc_type in ['liability', 'equity']:
            balance *= -1

        entry = {'name': name, 'balance': balance}

        if acc_type == 'asset':
            assets.append(entry)
            totals['asset'] += balance
        elif acc_type == 'liability':
            liabilities.append(entry)
            totals['liability'] += balance
        elif acc_type == 'equity':
            equity.append(entry)
            totals['equity'] += balance

    # 🧠 Retained Earnings (Net Profit)
    sales = SaleItem.objects.filter(sale__store=store, sale__sale_date__date__lte=as_of_date).aggregate(
        total_sales=Sum(F('unit_price') * F('quantity'), output_field=DecimalField(max_digits=20, decimal_places=2)),
        total_cost=Sum(F('cost_price') * F('quantity'), output_field=DecimalField(max_digits=20, decimal_places=2))
    )
    income = (sales['total_sales'] or 0) - (sales['total_cost'] or 0)

    expenses = ExpenseEntry.objects.filter(store=store, date__lte=as_of_date).aggregate(
        total_expenses=Sum('amount')
    )
    net_profit = income - (expenses['total_expenses'] or 0)

    equity.append({'name': 'Retained Earnings', 'balance': net_profit})
    totals['equity'] += net_profit

    return render(request, 'accounting/balance_sheet.html', {
        'assets': assets,
        'liabilities': liabilities,
        'equity': equity,
        'totals': totals,
        'stores': store_qs,
        'selected_store_id': store.id,
        'as_of_date': as_of_date,
    })

# from django.template.loader import get_template
# from django.http import HttpResponse
# from xhtml2pdf import pisa
from .utils import get_balance_sheet_context
# from inventory.models import CompanyProfile


@login_required
def balance_sheet_pdf_view(request):
    company = CompanyProfile.objects.first()
    store_id = request.GET.get("store")
    store = Store.objects.filter(id=store_id).first() if store_id else None

    if request.user.role == 'manager':
        if not store or store not in request.user.stores.all():
            store = request.user.stores.first()

    context = get_balance_sheet_context(store)
    context.update({
        'store': store,
        'company': company,
        'date': now().date(),
    })

    template = get_template("accounting/balance_sheet_pdf.html")
    html = template.render(context)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=balance_sheet.pdf"
    pisa.CreatePDF(html, dest=response)

    return response


# from django.db.models import Sum, Q
# from accounting.models import TransactionLine, Account
# from inventory.models import Store

@login_required
def trial_balance_view(request):
    user = request.user
    selected_store_id = request.GET.get('store')

    # Admins/superusers can access all stores
    if user.is_superuser or user.role == 'admin':
        allowed_stores = Store.objects.all()
        show_all_option = True
    else:
        allowed_stores = user.stores.all()
        show_all_option = False

    active_store = None
    if selected_store_id == 'all' and show_all_option:
        # Admin selected 'All Stores'
        transaction_lines = TransactionLine.objects.all()
    else:
        # Determine the active store (first or selected)
        try:
            active_store = allowed_stores.get(id=selected_store_id) if selected_store_id else allowed_stores.first()
        except Store.DoesNotExist:
            active_store = allowed_stores.first()

        transaction_lines = TransactionLine.objects.filter(transaction__store=active_store)

    # Group and sum per account
    lines = (
        transaction_lines
        .values('account__name')
        .annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )
        .order_by('account__name')
    )

    total_debit = sum(item['total_debit'] or 0 for item in lines)
    total_credit = sum(item['total_credit'] or 0 for item in lines)

    return render(request, 'accounting/trial_balance.html', {
        'lines': lines,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'active_store': active_store,
        'stores': allowed_stores,
        'show_all_option': show_all_option,
        'selected_store_id': selected_store_id,
    })

# dashboard/views.py
from django.contrib.auth.decorators import login_required
from accounting.models import Notification
@login_required
def notifications_list(request):
    notifications = request.user.notifications.order_by('-created_at')
    return render(request, 'dashboard/notifications.html', {'notifications': notifications})


# dashboard/views.py
# from django.shortcuts import get_object_or_404, redirect
# from accounting.models import Notification
# from django.contrib.auth.decorators import login_required

@login_required
def notification_redirect(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    
    # Mark as read
    notification.is_read = True
    notification.save()

    # Redirect to the target URL
    if notification.url:
        return redirect(notification.url)
    else:
        return redirect('dashboard:notifications_list')  # fallback


@login_required
def general_ledger_view(request):
    form = GeneralLedgerForm(request.GET or None, request=request)  # ✅ Pass request here
    lines = []
    total_debit = total_credit = 0

    user = request.user
    is_admin = user.is_superuser or user.role == 'admin'
    user_stores = user.stores.all()

    if form.is_valid():
        account = form.cleaned_data['account']
        selected_store = form.cleaned_data['store']
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']

        qs = TransactionLine.objects.filter(account=account).select_related('transaction')

        # 🏪 Store filter:
        if is_admin:
            if selected_store:
                qs = qs.filter(transaction__store=selected_store)
        else:
            allowed_store_ids = user_stores.values_list('id', flat=True)
            if selected_store and selected_store.id in allowed_store_ids:
                qs = qs.filter(transaction__store=selected_store)
            else:
                qs = qs.filter(transaction__store__in=allowed_store_ids)

        # 📅 Date filtering
        if start_date:
            qs = qs.filter(transaction__created_at__gte=start_date)
        if end_date:
            qs = qs.filter(transaction__created_at__lte=end_date)

        qs = qs.order_by('transaction__created_at', 'id')

        running_balance = 0
        for line in qs:
            running_balance += (line.debit or 0) - (line.credit or 0)
            lines.append({
                'date': line.transaction.created_at,
                'description': line.transaction.description,
                'debit': line.debit,
                'credit': line.credit,
                'balance': running_balance
            })
            total_debit += line.debit or 0
            total_credit += line.credit or 0

    return render(request, 'accounting/general_ledger.html', {
        'form': form,
        'lines': lines,
        'total_debit': total_debit,
        'total_credit': total_credit
    })

def build_customer_ledger(customer, from_date_str=None, to_date_str=None, user=None):
    from_date = parse_date_with_tz(from_date_str)
    to_date = parse_date_with_tz(to_date_str, end_of_day=True)

    invoices = Sale.objects.filter(customer=customer, sale_type='invoice')
    payments = CustomerPayment.objects.filter(customer=customer)

    # 🔐 Restrict to user's stores if manager
    if user and user.role == 'manager':
        allowed_stores = user.stores.all()
        invoices = invoices.filter(store__in=allowed_stores)
        payments = payments.filter(transaction__store__in=allowed_stores)

    # 📆 Apply date filters
    if from_date:
        invoices = invoices.filter(sale_date__gte=from_date)
        payments = payments.filter(created_at__gte=from_date)
    if to_date:
        invoices = invoices.filter(sale_date__lt=to_date)
        payments = payments.filter(created_at__lt=to_date)

    # 🧾 Combine entries
    invoices = invoices.annotate(entry_type=Value('Invoice'), entry_amount=F('total_amount'), date=F('sale_date'))
    payments = payments.annotate(entry_type=Value('Payment'), entry_amount=F('amount'), date=F('created_at'))

    transactions = sorted(chain(invoices, payments), key=lambda x: x.date)

    # 🧮 Build running ledger
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


@login_required
def customer_list_with_balances(request):
    query = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', '')

    customers = Customer.objects.all()

    # 🔐 Restrict to manager's store(s)
    if request.user.role == 'manager':
        from django.db.models import OuterRef, Exists

        # Get the stores the user has access to
        store_ids = request.user.stores.values_list('id', flat=True)

        # Limit customers to those with sales or payments in allowed stores
        from django.db.models import OuterRef, Exists

        store_ids = request.user.stores.values_list('id', flat=True)

        customers = customers.annotate(
            has_sales=Exists(
                Sale.objects.filter(customer=OuterRef('pk'), store__in=store_ids)
            ),
            has_payments=Exists(
                CustomerPayment.objects.filter(customer=OuterRef('pk'), transaction__store__in=store_ids)
            )
        ).filter(Q(has_sales=True) | Q(has_payments=True))

    if query:
        customers = customers.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )

    customer_data = []

    for customer in customers:
        # 🔁 Restrict sales and payments to manager’s stores
        sales_qs = Sale.objects.filter(customer=customer, sale_type='invoice')
        payments_qs = CustomerPayment.objects.filter(customer=customer)

        if request.user.role == 'manager':
            sales_qs = sales_qs.filter(store__in=request.user.stores.all())
            payments_qs = payments_qs.filter(transaction__store__in=request.user.stores.all())

        total_invoiced = sales_qs.aggregate(total=Coalesce(Sum('total_amount'), Decimal('0.00')))['total']
        total_paid = payments_qs.aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))['total']
        balance = total_invoiced - total_paid

        customer_data.append({
            'customer': customer,
            'invoiced': total_invoiced,
            'paid': total_paid,
            'balance': balance
        })

    # 🔁 Sorting
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
    transaction_type = request.GET.get('type')

    ledger, running_balance = build_customer_ledger(customer, from_date, to_date, user=request.user)

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
    transaction_type = request.GET.get('type')
    company = CompanyProfile.objects.first()

    ledger, running_balance = build_customer_ledger(customer, from_date, to_date, user=request.user)

    if transaction_type:
        ledger = [entry for entry in ledger if entry['type'].lower() == transaction_type.lower()]
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
        'type': transaction_type,
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



@login_required
def account_ledger_view(request, slug):
    account = get_object_or_404(Account, slug=slug)
    user = request.user

    # Base queryset
    transaction_lines = TransactionLine.objects.filter(account=account)

    # Multi-store filtering for managers
    if not user.is_superuser and user.role == 'manager':
        allowed_store_ids = user.stores.values_list('id', flat=True)
        transaction_lines = transaction_lines.filter(transaction__store__in=allowed_store_ids)

    # Add selects + ordering
    transaction_lines = transaction_lines.select_related('transaction').order_by(
        'transaction__created_at', 'id'
    )

    # Balance Calculation
    balance = Decimal(account.opening_balance or 0)
    history = []

    for line in transaction_lines:
        balance += Decimal(line.debit or 0) - Decimal(line.credit or 0)
        history.append({
            'date': line.transaction.created_at,
            'description': line.transaction.description,
            'debit': line.debit,
            'credit': line.credit,
            'balance': balance,
            'store': line.transaction.store.name if line.transaction.store else 'N/A',
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
                store = request.user.get_active_store(request)
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

    # For managers, calculate across all their stores
    if user.role == 'manager':
        stores = user.stores.all()
        balances = calculate_account_balances(stores=stores)
    else:
        balances = calculate_account_balances()

    return render(request, 'accounting/account_balances.html', {
        'balances': balances
    })


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

    store = get_user_allowed_store(request, store_id)

    # Date range
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
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d").date() if start else date(today.year, today.month, 1)
            end_date = datetime.strptime(end, "%Y-%m-%d").date() if end else today
        except ValueError:
            start_date = date(today.year, today.month, 1)
            end_date = today

    context = get_profit_loss_context(start_date, end_date, store=store)

    # 🔒 Restrict store list
    if request.user.is_superuser or request.user.role == 'admin':
        context['stores'] = Store.objects.all()
    else:
        context['stores'] = request.user.stores.all()

    context['selected_store_id'] = store.id if store else None

    return render(request, 'accounting/profit_loss_report.html', context)

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

    store = get_user_allowed_store(request, store_id)

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

    # 🔁 Date Parsing
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
        start_date = parse_date_safe(request.GET.get('start_date')) or date(today.year, today.month, 1)
        end_date = parse_date_safe(request.GET.get('end_date')) or today

    # 🔐 Store access control
    store = get_user_allowed_store(request, store_id)

    # 📦 Sales
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

    sales_data, total_sales, total_cost, total_profit = [], 0, 0, 0
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

    # 💸 Expenses
    expenses_qs = ExpenseEntry.objects.filter(date__range=(start_date, end_date))
    if store:
        expenses_qs = expenses_qs.filter(store=store)

    expense_data, total_expenses = [], 0
    for exp in expenses_qs.values('expense_account__name').annotate(total_expense=Sum('amount')):
        expense_data.append({
            'category': exp['expense_account__name'],
            'amount': exp['total_expense'],
        })
        total_expenses += exp['total_expense'] or 0

    gross_profit = total_sales - total_cost
    net_profit = gross_profit - total_expenses

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'sales_data': sales_data,
        'expense_data': expense_data,
        'stores': Store.objects.all() if request.user.is_superuser or request.user.role == 'admin' else request.user.stores.all(),
        'selected_store_id': store.id if store else None,
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
    start_date = parse_date_safe(request.GET.get('start_date'))
    end_date = parse_date_safe(request.GET.get('end_date'))
    store_id = request.GET.get('store')

    if not start_date or not end_date:
        return HttpResponse("Invalid dates provided", status=400)

    # 🔐 Restrict store access
    store = get_user_allowed_store(request, store_id)

    # 📦 Sales
    sales_qs = SaleItem.objects.filter(sale__sale_date__date__range=(start_date, end_date))
    if store:
        sales_qs = sales_qs.filter(sale__store=store)

    sales_qs = (
        sales_qs
        .values('product__name', 'unit_price', 'cost_price')
        .annotate(quantity=Sum('quantity'))
        .order_by('product__name')
    )

    items, total_quantity, total_sales, total_cost, total_profit = [], 0, 0, 0, 0
    for item in sales_qs:
        quantity = item['quantity'] or 0
        unit_price = item['unit_price'] or 0
        cost_price = item['cost_price'] or 0
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

    # 💸 Expenses
    expense_qs = ExpenseEntry.objects.filter(date__range=(start_date, end_date))
    if store:
        expense_qs = expense_qs.filter(store=store)

    expense_data, total_expenses = [], 0
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
