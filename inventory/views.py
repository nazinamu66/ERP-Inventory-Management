from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.http import HttpResponse
from inventory.models import StockTransfer,Supplier
from inventory.forms import StockTransferForm
from .forms import StockAdjustmentForm, ProductWithStockForm
from .models import Product, Store, StockAdjustment
from django.core.paginator import Paginator
from .forms import SaleForm, SaleItemFormSet
from django.db.models import Q
from users.models import User
import csv
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.utils.safestring import mark_safe
from .forms import PurchaseOrderForm, PurchaseOrderItem, PurchaseOrderItemForm, PurchaseOrder
from django.forms import modelformset_factory
from .forms import SupplierForm
from .models import CompanyProfile, Purchase
from django.utils.timezone import now, timedelta
from django.db import models
from datetime import datetime
from django.conf import settings
from weasyprint import HTML
from .forms import CustomerForm
from django.template.loader import render_to_string
import weasyprint
from .forms import SaleReturnForm, SaleReturnItemFormSet, SaleReturnItem
from django.forms import inlineformset_factory
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_POST
from accounting.services import record_transaction
import logging
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Sale, SaleItem, Stock
from django.db.models import Sum
from .forms import InvoiceForm
from .models import AuditLog
from users.models import User 
from django.http import HttpResponseRedirect
import os
from django.contrib.staticfiles import finders
from accounting.services import reverse_transaction
from django.utils import timezone
from django.views.generic import View

from django.shortcuts import render, redirect
from .models import Product  # adjust if your model is elsewhere

def scan_product(request):
    return render(request, "inventory/scan_product.html")


def handle_scan_redirect(request):
    code = request.GET.get("code", "").strip()
    try:
        product = Product.objects.get(barcode=code)
        return render(request, "inventory/scan_result.html", {"product": product})
    except Product.DoesNotExist:
        return render(request, "inventory/scan_product.html", {
            "error": f"No product found for code: {code}"
        })

class ServiceWorkerView(View):
    def get(self, request, *args, **kwargs):
        sw_path = os.path.join(settings.BASE_DIR, 'static/js/service-worker.js')
        with open(sw_path, 'rb') as f:
            return HttpResponse(f.read(), content_type='application/javascript')


@login_required
def convert_quotation_to_invoice(request, quotation_id):
    quotation = get_object_or_404(Quotation.objects.prefetch_related('items'), id=quotation_id)

    # 🚫 Prevent unauthorized access
    if not request.user.is_superuser and quotation.store not in request.user.stores.all():
        return HttpResponseForbidden("You do not have permission to convert this quotation.")

    try:
        with transaction.atomic():
            # ✅ Create invoice (Sale object)
            sale = Sale.objects.create(
                customer=quotation.customer,
                store=quotation.store,
                sale_type='invoice',
                sold_by=request.user,
                payment_status='unpaid',
                total_amount=quotation.total_amount(),  # ✅ Call the method
                amount_paid=Decimal('0.00'),
                balance_due=quotation.total_amount(),    # ✅ Also call method
            )

            # ✅ Assign receipt number
            sale.receipt_number = f"INV-{sale.id:06d}"
            sale.save(update_fields=["receipt_number"])

            total_cogs = Decimal('0.00')

            for item in quotation.items.all():
                stock_entry = Stock.objects.filter(product=item.product, store=quotation.store).first()

                if not stock_entry or stock_entry.quantity < item.quantity:
                    raise ValueError(f"Insufficient stock for {item.product.name}")

                stock_entry.quantity -= item.quantity
                stock_entry.save(update_fields=["quantity"])

                SaleItem.objects.create(
                    sale=sale,
                    product=item.product,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    cost_price=stock_entry.cost_price or 0
                )

                total_cogs += item.quantity * (stock_entry.cost_price or 0)

            # ✅ Record transactions
            revenue_txn = record_transaction_by_slug(
                source_slug='sales-revenue',
                destination_slug='accounts-receivable',
                amount=sale.total_amount,
                store=sale.store,
                description=f"Invoice - {sale.receipt_number}"
            )

            cogs_txn = record_transaction_by_slug(
                source_slug='inventory-assets',
                destination_slug='cost-of-goods-sold',
                amount=total_cogs,
                store=sale.store,
                description=f"COGS for {sale.receipt_number}"
            )

            sale.revenue_transaction = revenue_txn
            sale.cogs_transaction = cogs_txn
            sale.transaction = revenue_txn
            sale.save(update_fields=["revenue_transaction", "cogs_transaction", "transaction"])

            # 🔍 Audit Log
            AuditLog.objects.create(
                user=request.user,
                action='quotation_to_invoice',
                description=f"Converted quotation #{quotation.id} to invoice {sale.receipt_number}",
                store=sale.store
            )
            
            quotation.converted_sale = sale
            quotation.save(update_fields=['converted_sale'])

            messages.success(request, f"Quotation converted to Invoice {sale.receipt_number}.")
            return redirect('inventory:sale_detail', sale.id)

    except Exception as e:
        logger.error(f"❌ Conversion failed: {e}")
        messages.error(request, f"Failed to convert quotation: {e}")
        return redirect('inventory:quotation_detail', quotation.id)
    
# # views.py

@login_required
def quotation_edit(request, quotation_id):
    quotation = get_object_or_404(Quotation.objects.prefetch_related('items'), id=quotation_id)

    if not request.user.is_superuser and quotation.store not in request.user.stores.all():
        return HttpResponseForbidden("Access Denied: You don't have permission to edit this quotation.")

    if request.method == 'POST':
        form = QuotationForm(request.POST, instance=quotation)
        formset = QuotationItemFormSet(request.POST, instance=quotation)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()

                AuditLog.objects.create(
                    user=request.user,
                    action='quotation_edit',
                    description=f"Edited Quotation #{quotation.id}",
                    store=quotation.store
                )

                messages.success(request, f"Quotation #{quotation.id} updated successfully.")
                return redirect('inventory:quotation_detail', quotation.id)
    else:
        form = QuotationForm(instance=quotation)
        formset = QuotationItemFormSet(instance=quotation)

    return render(request, 'dashboard/quotation_form.html', {
        'form': form,
        'formset': formset,
        'editing': True,
        'quotation': quotation,
    })


# views.py
from django.views.decorators.http import require_POST

@login_required
@require_POST
def quotation_delete(request, quotation_id):
    quotation = get_object_or_404(Quotation, id=quotation_id)

    if not request.user.is_superuser and quotation.store not in request.user.stores.all():
        return HttpResponseForbidden("Access Denied: You don't have permission to delete this quotation.")

    quotation.delete()

    AuditLog.objects.create(
        user=request.user,
        action='quotation_delete',
        description=f"Deleted Quotation #{quotation.id}",
        store=quotation.store
    )

    messages.success(request, f"Quotation #{quotation_id} deleted successfully.")
    return redirect('inventory:quotation_list')



@login_required
def customer_create(request):
    next_url = request.GET.get('next', request.path)

    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.created_by = request.user
            customer.save()

            # ✅ Determine store (only if user has one)
            user_store = request.user.stores.first() if hasattr(request.user, 'stores') else None

            # ✅ Audit log
            AuditLog.objects.create(
                user=request.user,
                action='create_customer',
                store=user_store,
                description=f"{request.user.username} created customer '{customer.name}'"
            )

            messages.success(request, "Customer added successfully.")
            return HttpResponseRedirect(next_url)
    else:
        form = CustomerForm()

    return render(request, 'dashboard/customer_form.html', {
        'form': form,
        'next': next_url,
    })



@login_required
def supplier_list(request):
    if not request.user.is_superuser and request.user.role != 'manager':
        messages.error(request, "Not authorized.")
        return render(request, 'errors/permission_denied.html', status=403)

    suppliers = Supplier.objects.all().order_by('name')
    return render(request, 'dashboard/supplier_list.html', {'suppliers': suppliers})


@login_required
def supplier_edit(request, supplier_id):
    if not request.user.is_superuser:
        messages.error(request, "Only admins can edit suppliers.")
        return render(request, 'errors/permission_denied.html', status=403)

    supplier = get_object_or_404(Supplier, pk=supplier_id)
    form = SupplierForm(request.POST or None, instance=supplier)
    if form.is_valid():
        form.save()
        messages.success(request, "Supplier updated successfully.")
        return redirect('inventory:supplier_list')

    return render(request, 'dashboard/supplier_form.html', {'form': form, 'supplier': supplier})


from decimal import Decimal
from django.template.loader import get_template
from weasyprint import HTML
from django.http import HttpResponse, HttpResponseForbidden

# utils.py or inline
from django.conf import settings
import os

def link_callback(uri, rel):
    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
        return path
    return uri



@login_required
def export_po_pdf(request, po_id):
    po = get_object_or_404(PurchaseOrder, pk=po_id)

    if not request.user.is_superuser and request.user.role != 'admin' and request.user != po.created_by:
        return render(request, 'errors/permission_denied.html', status=403)

    goods_total = sum(item.subtotal for item in po.items.all())
    expenses_qs = ExpenseEntry.objects.filter(purchase_orders=po)
    expenses_total = expenses_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    grand_total = goods_total + expenses_total

    company = po.store.company_profile if po.store and po.store.company_profile else CompanyProfile.objects.first()

    template = get_template('pdf/po_receipt.html')
    html = template.render({
        'po': po,
        'goods_total': goods_total,
        'expenses_total': expenses_total,
        'grand_total': grand_total,
        'company': company,
    }, request=request)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="PO-{po.id}.pdf"'

    pisa.CreatePDF(html, dest=response, link_callback=link_callback)
    return response


@login_required
def inventory_report_view(request):
    user = request.user
    role = getattr(user, 'role', '').lower()
    store = getattr(user, 'store', None)

    # Reset filters
    if 'clear' in request.GET:
        return redirect('inventory:inventory_report')

    stocks = Stock.objects.select_related('product', 'store')

    # Visibility control
    if role in ['manager', 'clerk', 'sales'] and store:
        stocks = stocks.filter(store=store)
        allowed_stores = Store.objects.filter(id=store.id)
    else:
        store_id = request.GET.get('store')
        if store_id:
            stocks = stocks.filter(store_id=store_id)
        allowed_stores = Store.objects.all()

    product_id = request.GET.get('product')
    if product_id:
        stocks = stocks.filter(product_id=product_id)

    # Totals
    total_quantity = sum(s.quantity for s in stocks)
    total_value = sum(s.quantity * (s.cost_price or 0) for s in stocks)

    return render(request, 'dashboard/inventory_report.html', {
        'stocks': stocks,
        'products': Product.objects.all(),
        'stores': allowed_stores,
        'selected_product': product_id,
        'selected_store': request.GET.get('store', ''),
        'total_quantity': total_quantity,
        'total_value': total_value,
    })


@login_required
def export_inventory_csv(request):
    role = getattr(request.user, 'role', '').lower()
    store = getattr(request.user, 'store', None)

    stocks = Stock.objects.select_related('product', 'store')
    if role == 'staff' and store:
        stocks = stocks.filter(store=store)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Product', 'Store', 'Quantity', 'Last Updated'])

    for s in stocks:
        writer.writerow([
            s.product.name,
            s.store.name,
            s.quantity,
            s.last_updated.strftime('%Y-%m-%d %H:%M')
        ])

    return response


def link_callback(uri, rel):
    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    elif uri.startswith(settings.STATIC_URL):
        path = finders.find(uri.replace(settings.STATIC_URL, ""))
    else:
        return uri
    if not os.path.isfile(path):
        raise Exception('Media URI must start with STATIC_URL or MEDIA_URL')
    return path


@login_required
def export_inventory_pdf(request):
    from .models import CompanyProfile
    from django.utils.timezone import now

    role = getattr(request.user, 'role', '').lower()
    store = getattr(request.user, 'store', None)

    stocks = Stock.objects.select_related('product', 'store')
    if role == 'staff' and store:
        stocks = stocks.filter(store=store)

    # Filters
    product_id = request.GET.get('product')
    store_id = request.GET.get('store')

    if product_id and product_id.isdigit():
        stocks = stocks.filter(product_id=int(product_id))
    if store_id and store_id.isdigit() and role != 'staff':
        stocks = stocks.filter(store_id=int(store_id))

    # Totals
    total_quantity = sum(s.quantity for s in stocks)
    total_value = sum(s.quantity * (s.cost_price or 0) for s in stocks)

    context = {
        'stocks': stocks,
        'user': request.user,
        'now': now(),
        'company': CompanyProfile.objects.first(),
        'total_quantity': total_quantity,
        'total_value': total_value,
    }

    template = get_template('pdf/inventory_report_pdf.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="inventory_report.pdf"'
    pisa.CreatePDF(html, dest=response, link_callback=link_callback)
    return response


@login_required
def redirect_dashboard(request):
    role = getattr(request.user, 'role', '').strip().lower()

    if request.user.is_superuser or role == 'admin':
        return redirect('admin_dashboard')
    elif role == 'manager':
        return redirect('manager_dashboard')
    elif role == 'staff':
        return redirect('store_dashboard')
    elif role in ['clerk', 'inventory clerk']:
        return redirect('inventory_dashboard')
    elif role == 'sales':
        return redirect('sales_dashboard')
    else:
        return redirect('default_dashboard')

from accounting.models import  ExpenseEntry
from django.db.models import Sum
from decimal import Decimal

@login_required
def purchase_order_detail(request, po_id):
    po = get_object_or_404(
        PurchaseOrder.objects.prefetch_related('items__product', 'expenses'),
        id=po_id
    )

    goods_total = sum(item.subtotal for item in po.items.all())

    expenses_total = po.expenses.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    grand_total = goods_total + expenses_total

    return render(request, 'dashboard/purchase_order_detail.html', {
        'po': po,
        'goods_total': goods_total,
        'expenses_total': expenses_total,
        'grand_total': grand_total,
    })



from accounting.utils import notify_users
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@login_required
def receive_purchase_order(request, po_id):
    po = get_object_or_404(PurchaseOrder, pk=po_id)

    if po.status == 'received':
        messages.warning(request, "This PO has already been marked as received.")
        return redirect('inventory:purchase_order_detail', po_id=po.id)

    store = None
    if request.method == 'POST':
        if request.user.is_superuser or request.user.role == 'admin':
            store_id = request.POST.get('store')
            store = get_object_or_404(Store, id=store_id)
        else:
            store_id = request.POST.get('store') or None
            if not store_id or not request.user.stores.filter(id=store_id).exists():
                return HttpResponseForbidden("You do not have permission to receive stock at this store.")
            store = get_object_or_404(Store, id=store_id)

        try:
            with transaction.atomic():
                total_value = 0

                for item in po.items.select_related('product'):
                    product = item.product
                    quantity = item.quantity
                    unit_price = item.unit_price

                    product.total_quantity += quantity
                    product.save()

                    stock, created = Stock.objects.get_or_create(
                        product=product,
                        store=store,
                        defaults={'quantity': quantity, 'cost_price': unit_price}
                    )

                    if not created:
                        stock.quantity += quantity
                        stock.cost_price = unit_price
                        stock.save(update_fields=['quantity', 'cost_price'])

                    total_value += quantity * unit_price

                # ✅ Update PO status and store
                po.status = 'received'
                po.store = store
                po.save()

                # ✅ Audit log
                AuditLog.objects.create(
                    user=request.user,
                    action='adjustment',
                    store=store,
                    description=f"{request.user.username} received PO-{po.id} and updated stock at {store.name}."
                )

                # ✅ Create accounting entry
                from accounting.services import record_transaction_by_slug
                record_transaction_by_slug(
                    source_slug="accounts-payable",
                    destination_slug="inventory-assets",
                    amount=total_value,
                    description=f"PO-{po.id} Goods Received",
                    supplier=po.supplier,
                    store=store
                )

                # ✅ Notify admins and store managers
                managers = store.user_set.filter(role='manager')
                admins = User.objects.filter(is_superuser=True)
                recipients = list(managers) + list(admins)

                notify_users(
                    users=recipients,
                    message=f"PO-{po.id} was received at {store.name} by {request.user.username}.",
                    url=reverse('inventory:purchase_order_detail', kwargs={'po_id': po.id})  # ✅ Corrected
                )


                messages.success(request, "Purchase Order received and accounting recorded.")
                return redirect('inventory:purchase_order_detail', po_id=po.id)

        except Exception as e:
            logger.error(f"❌ PO receiving failed: {e}")
            messages.error(request, f"An error occurred: {e}")

    stores = Store.objects.all() if request.user.is_superuser or request.user.role == 'admin' else request.user.stores.all()

    return render(request, 'dashboard/receive_purchase_order.html', {
        'po': po,
        'stores': stores,
    })

@require_POST
@login_required
def purchase_received_delete_view(request, po_id):
    po = get_object_or_404(PurchaseOrder, pk=po_id)

    # ✅ Role & Access Check
    if not request.user.is_superuser and request.user.role != 'manager':
        return HttpResponseForbidden("Only managers or admins can delete received purchases.")

    # ✅ Store ownership check
    if not request.user.is_superuser and po.store not in request.user.stores.all():
        return HttpResponseForbidden("You do not have access to delete POs from this store.")

    if po.status != 'received':
        messages.error(request, "Only received POs can be deleted.")
        return redirect('inventory:purchase_order_detail', po_id=po.id)

    try:
        with transaction.atomic():
            for item in po.items.select_related('product'):
                product = item.product
                quantity = item.quantity

                product.total_quantity = max(product.total_quantity - quantity, 0)
                product.save(update_fields=["total_quantity"])

                if po.store:
                    stock = Stock.objects.filter(product=product, store=po.store).first()
                    if stock:
                        stock.quantity = max(stock.quantity - quantity, 0)
                        stock.save(update_fields=["quantity"])

            # Reverse accounting transaction
            from accounting.models import Transaction
            related_txn = Transaction.objects.filter(description__icontains=f"PO-{po.id} Goods Received").first()

            if related_txn:
                from accounting.services import reverse_transaction
                reverse_transaction(related_txn.id, reason=f"Deleted Received PO-{po.id}")

            po.delete()

            AuditLog.objects.create(
                user=request.user,
                store=po.store,
                action='adjustment',
                description=f"{request.user.username} deleted PO-{po.id} and reversed stock/accounting."
            )

            messages.success(request, f"PO-{po.id} deleted and reversed.")
            return redirect('inventory:purchase_order_list')

    except Exception as e:
        logger.error(f"❌ Error deleting PO-{po.id}: {e}")
        messages.error(request, f"An error occurred: {e}")
        return redirect('inventory:purchase_order_detail', po_id=po.id)

@login_required
def purchase_order_list(request):
    user = request.user
    purchase_orders = PurchaseOrder.objects.select_related('supplier', 'created_by').order_by('-date')

    supplier_id = request.GET.get('supplier')
    status = request.GET.get('status')
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')

    # 🔐 Restrict for managers
    if not user.is_superuser and user.role == 'manager':
        user_store_ids = user.stores.values_list('id', flat=True)
        purchase_orders = purchase_orders.filter(
            models.Q(store__in=user_store_ids) | models.Q(store__isnull=True)
        )

    if supplier_id:
        purchase_orders = purchase_orders.filter(supplier_id=supplier_id)

    if status:
        purchase_orders = purchase_orders.filter(status=status)

    if start_date:
        purchase_orders = purchase_orders.filter(date__gte=start_date)

    if end_date:
        purchase_orders = purchase_orders.filter(date__lte=end_date)

    suppliers = Supplier.objects.all()

    return render(request, 'dashboard/purchase_order_list.html', {
        'orders': purchase_orders,
        'suppliers': suppliers,
        'selected_supplier': supplier_id,
        'selected_status': status,
        'start_date': start_date,
        'end_date': end_date,
    })


@login_required
def add_supplier(request):
    if not request.user.is_superuser and request.user.role != 'manager':
        messages.error(request, "Not authorized.")
        return render(request, 'errors/permission_denied.html', status=403)

    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Supplier added successfully.")
            return redirect('inventory:create_purchase_order')
    else:
        form = SupplierForm()

    return render(request, 'dashboard/supplier_form.html', {'form': form})


@login_required
def delete_sale(request, sale_id):
    sale = get_object_or_404(Sale, pk=sale_id)

    if request.method == "POST":
        try:
            with transaction.atomic():
                from accounting.services import reverse_transaction

                if sale.revenue_transaction:
                    reverse_transaction(sale.revenue_transaction.id, reason=f"Sale Reversal: {sale.receipt_number}")

                if sale.cogs_transaction:
                    reverse_transaction(sale.cogs_transaction.id, reason=f"COGS Reversal: {sale.receipt_number}")

                for item in sale.items.all():
                    stock, _ = Stock.objects.get_or_create(product=item.product, store=sale.store)
                    stock.quantity += item.quantity
                    stock.save()

                sale.delete()

                messages.success(request, "Sale deleted, stock restored, and accounting fully reversed.")
                return redirect('inventory:sale_list')

        except Exception as e:
            logger.error(f"❌ Deletion failed: {e}")
            messages.error(request, "Something went wrong while deleting the sale.")

    return render(request, 'dashboard/confirm_delete.html', {'object': sale, 'type': 'Sale'})


from django.db.models import Q

@login_required
def export_sales_pdf(request):
    sales = Sale.objects.select_related('store', 'sold_by').order_by('-sale_date')

    product = request.GET.get('product')
    store_id = request.GET.get('store')
    sold_by = request.GET.get('sold_by')
    start = request.GET.get('start')
    end = request.GET.get('end')

    filters = {}

    # ✅ Restrict data for non-admin users
    if not request.user.is_superuser and request.user.role != 'admin':
        allowed_store_ids = request.user.stores.values_list('id', flat=True)
        sales = sales.filter(store__in=allowed_store_ids)

        # ✅ Validate that the user can access the `store_id` they passed
        if store_id and int(store_id) not in allowed_store_ids:
            return HttpResponse("Access Denied: You don't have permission to access this store.", status=403)
    else:
        allowed_store_ids = Store.objects.values_list('id', flat=True)  # Admins can access all

    # ✅ Filters
    if product:
        sales = sales.filter(items__product_id=product).distinct()  # Correct relation
        filters['product'] = Product.objects.filter(id=product).first()

    if store_id:
        sales = sales.filter(store_id=store_id)
        filters['store'] = Store.objects.filter(id=store_id).first()

    if sold_by:
        sales = sales.filter(sold_by_id=sold_by)
        filters['user'] = User.objects.filter(id=sold_by).first()

    if start and end:
        sales = sales.filter(sale_date__range=[start, end])
        filters['start'] = start
        filters['end'] = end

    # ✅ Render PDF
    template = get_template('dashboard/sale_report_pdf.html')
    html = template.render({'sales': sales, 'filters': filters})

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'

    pisa.CreatePDF(src=html, dest=response)
    return response


@login_required
def export_purchase_orders_csv(request):
    orders = filter_purchase_orders(request)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="purchase_orders_{now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow(['PO ID', 'Supplier', 'Status', 'Date', 'Created By'])

    for po in orders:
        writer.writerow([
            f'PO-{po.id}',
            po.supplier.name,
            po.status.title(),
            po.date.strftime('%Y-%m-%d'),
            po.created_by.username if po.created_by else 'N/A',
        ])

    return response




def filter_purchase_orders(request):
    purchase_orders = PurchaseOrder.objects.select_related('supplier', 'created_by').order_by('-date')

    supplier_id = request.GET.get('supplier')
    status = request.GET.get('status')
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')

    # Return ALL if all filters are blank
    if not any([supplier_id, status, start_date, end_date]):
        return purchase_orders

    if supplier_id and supplier_id.isdigit():
        purchase_orders = purchase_orders.filter(supplier_id=int(supplier_id))

    if status:
        purchase_orders = purchase_orders.filter(status=status)

    try:
        if start_date and start_date.lower() != "none":
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            purchase_orders = purchase_orders.filter(date__gte=start_date_obj)
    except Exception as e:
        print(f"[FILTER] Start date error: {e}")

    try:
        if end_date and end_date.lower() != "none":
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            purchase_orders = purchase_orders.filter(date__lte=end_date_obj)
    except Exception as e:
        print(f"[FILTER] End date error: {e}")

    return purchase_orders


import csv
from django.db.models import Q

@login_required
def export_sales_csv(request):
    sales = Sale.objects.select_related('store', 'sold_by').prefetch_related('items__product').order_by('-sale_date')

    product_id = request.GET.get('product')
    store_id = request.GET.get('store')
    sold_by_id = request.GET.get('sold_by')
    start = request.GET.get('start')
    end = request.GET.get('end')

    # ✅ Restrict to allowed stores
    if not request.user.is_superuser and request.user.role != 'admin':
        allowed_store_ids = list(request.user.stores.values_list('id', flat=True))
        sales = sales.filter(store__in=allowed_store_ids)

        if store_id and int(store_id) not in allowed_store_ids:
            return HttpResponse("Access Denied: You don't have permission to access this store.", status=403)

    if store_id:
        sales = sales.filter(store_id=store_id)
    if sold_by_id:
        sales = sales.filter(sold_by_id=sold_by_id)
    if start and end:
        sales = sales.filter(sale_date__range=[start, end])
    if product_id:
        sales = sales.filter(items__product_id=product_id).distinct()

    # ✅ CSV Response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Product', 'Quantity', 'Unit Price', 'Subtotal', 'Store', 'Sold By', 'Date'])

    # ✅ Flatten to SaleItem level
    for sale in sales:
        for item in sale.items.all():
            writer.writerow([
                item.product.name,
                item.quantity,
                item.unit_price,
                item.subtotal,
                sale.store.name,
                sale.sold_by.username if sale.sold_by else "Unknown",
                sale.sale_date.strftime("%Y-%m-%d %H:%M"),
            ])

    return response


@login_required
def audit_log_list_view(request):
    logs = AuditLog.objects.select_related("user", "store").order_by("-timestamp")
    users = User.objects.all()
    actions = AuditLog.objects.order_by("action").values_list("action", flat=True).distinct()

    user = request.user

    # 🔐 Managers: Restrict logs to their assigned stores
    if user.role == "manager":
        logs = logs.filter(Q(store__in=user.stores.all()) | Q(user=user))

    # 🔎 Filters
    user_id = request.GET.get("user")
    action = request.GET.get("action")
    start = request.GET.get("start")
    end = request.GET.get("end")
    q = request.GET.get("q", "").strip()

    if user_id:
        logs = logs.filter(user_id=user_id)

    if action:
        logs = logs.filter(action=action)

    if start and end:
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
            logs = logs.filter(timestamp__range=(start_date, end_date))
        except ValueError:
            pass

    if q:
        logs = logs.filter(Q(description__icontains=q) | Q(user__username__icontains=q))

    # 🧾 Export as PDF
    if request.GET.get("export") == "pdf":
        html = render_to_string("pdf/audit_log_pdf.html", {
            "logs": logs,
            "exported_at": now(),
        })
        pdf = HTML(string=html, base_url=request.build_absolute_uri()).write_pdf()
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=audit_logs.pdf"
        return response

    # 🗂 Pagination
    paginator = Paginator(logs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "dashboard/audit_log_list.html", {
        "page_obj": page_obj,
        "users": users,
        "action_choices": actions,
        "selected_user": user_id,
        "selected_action": action,
        "start": start,
        "end": end,
        "q": q,
    })


@login_required
def sale_return_view(request, sale_id):
    sale = get_object_or_404(Sale, pk=sale_id)
    sale_items = sale.items.all()
    sale_items_dict = {str(item.id): item for item in sale_items}

    if request.method == 'POST':
        form = SaleReturnForm(request.POST)
        formset = SaleReturnItemFormSet(request.POST, prefix="return")

        # 🔁 Restrict queryset of sale_item in POST as well
        for subform in formset.forms:
            subform.fields['sale_item'].queryset = sale_items

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                sale_return = form.save(commit=False)
                sale_return.sale = sale
                sale_return.returned_by = request.user
                sale_return.save()

                total = 0
                for item_form in formset:
                    return_item = item_form.save(commit=False)
                    sale_item = return_item.sale_item
                    return_qty = return_item.quantity_returned

                    if return_qty > 0:
                        stock = Stock.objects.get(product=sale_item.product, store=sale.store)
                        stock.quantity += return_qty
                        stock.save()

                        return_item.sale_return = sale_return
                        return_item.save()

                        total += return_qty * sale_item.unit_price

                sale_return.total_refunded = total
                sale_return.save()

                from accounting.services import record_transaction_by_slug
                record_transaction_by_slug(
                    source_slug="sales-revenue",
                    destination_slug="accounts-receivable",
                    amount=total,
                    description=f"Return for {sale.receipt_number}",
                    store=sale.store
                )

                messages.success(request, "Return processed successfully.")
                return redirect('inventory:sale_detail', pk=sale_id)
    else:
        form = SaleReturnForm()

        # ✅ Generate initial data for formset from sale items
        initial_data = [{'sale_item': item.id, 'quantity_returned': 0} for item in sale_items]

        formset = SaleReturnItemFormSet(
            prefix="return",
            queryset=SaleReturnItem.objects.none(),
            initial=initial_data
        )

        # ✅ Restrict the sale_item queryset to this sale only
        for subform in formset.forms:
            subform.fields['sale_item'].queryset = sale_items

    return render(request, 'dashboard/sale_return_form.html', {
        'form': form,
        'formset': formset,
        'sale': sale,
        'sale_items_dict': sale_items_dict,
    })


from django.db.models import Q
from django.core.paginator import Paginator
from django.db.models import Sum

@login_required
def sale_list_view(request):
    user = request.user
    sales = Sale.objects.select_related('customer', 'store', 'sold_by').prefetch_related('items__product').order_by('-sale_date')

    product_id = request.GET.get('product')
    store_id = request.GET.get('store')
    sold_by_id = request.GET.get('sold_by')
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    query = request.GET.get('q')

    # 🔐 Restrict access for non-admins
    if not user.is_superuser and user.role != 'admin':
        allowed_store_ids = list(user.stores.values_list('id', flat=True))
        sales = sales.filter(store__in=allowed_store_ids)

        if store_id and int(store_id) not in allowed_store_ids:
            return HttpResponse("Access Denied: You don't have permission to view this store's sales.", status=403)
    else:
        allowed_store_ids = Store.objects.values_list('id', flat=True)

    # 🔎 Apply Filters
    if query:
        sales = sales.filter(receipt_number__icontains=query)

    if product_id:
        sales = sales.filter(items__product_id=product_id).distinct()

    if store_id:
        sales = sales.filter(store_id=store_id)

    if sold_by_id:
        sales = sales.filter(sold_by_id=sold_by_id)

    if start_date and end_date:
        sales = sales.filter(sale_date__range=[start_date, end_date])

    total_revenue = sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_sales_count = sales.count()

    paginator = Paginator(sales.distinct(), 20)
    page = request.GET.get('page')
    sales_page = paginator.get_page(page)

    context = {
        'sales': sales_page,
        'products': Product.objects.all(),
        'stores': Store.objects.filter(id__in=allowed_store_ids),
        'users': User.objects.filter(stores__in=allowed_store_ids).distinct(),
        'total_revenue': total_revenue,
        'total_sales_count': total_sales_count,
    }

    return render(request, 'dashboard/sale_list.html', context)


@login_required
def sale_receipt_pdf(request, sale_id):
    sale = get_object_or_404(Sale.objects.select_related('store__company_profile').prefetch_related('items__product'), pk=sale_id)

    company = sale.store.company_profile  # ✅ Get company from the store

    logo_url = ""
    if company and company.logo:
        logo_url = request.build_absolute_uri(company.logo.url)

    context = {
        'sale': sale,
        'company': company,
        'logo_url': logo_url,
    }

    html_string = render_to_string('pdf/sale_receipt.html', context)
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="Receipt-{sale.receipt_number}.pdf"'
    return response

@login_required
def sale_detail_view(request, pk):
    sale = get_object_or_404(Sale.objects.select_related('customer', 'store', 'sold_by'), pk=pk)
    items = sale.items.select_related('product').all()
    total_profit = sum(item.profit for item in items)

    user = request.user
    # 👇 Only allow superusers or managers assigned to the sale's store to see profit
    can_view_profit = (
        user.is_superuser or
        (user.role == 'manager' and sale.store in user.stores.all())
    )

    return render(request, 'dashboard/sale_detail.html', {
        'sale': sale,
        'items': items,
        'total_profit': total_profit,
        'can_view_profit': can_view_profit,
    })


logger = logging.getLogger(__name__)

def audit_log_detail_view(request, pk):
    log = get_object_or_404(AuditLog, pk=pk)
    return render(request, "dashboard/log_detail.html", {"log": log})



from accounting.services import record_transaction_by_slug
from .models import Customer

@login_required
def sale_receipt_create(request):
    if request.user.role not in ['sales', 'clerk', 'manager', 'admin'] and not request.user.is_superuser:
        return render(request, 'errors/permission_denied.html', status=403)

    form = SaleForm(request.POST or None, request=request)
    formset = SaleItemFormSet(request.POST or None, prefix="form")

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        try:
            with transaction.atomic():
                sale = form.save(commit=False)
                sale.sold_by = request.user
                sale.sale_type = 'receipt'
                sale.payment_status = 'paid'

                # ✅ Multi-store enforcement
                if not request.user.is_superuser and sale.store not in request.user.stores.all():
                    return HttpResponse("Access Denied: You cannot assign sales to this store.", status=403)

                sale.save()

                # Generate receipt number if not already set
                if not sale.receipt_number:
                    sale.receipt_number = f"RCPT-{sale.id:06d}"
                    sale.save(update_fields=["receipt_number"])

                total, cost_total = 0, 0
                store = sale.store  # ✅ This is now safe to use

                for form_item in formset:
                    if form_item.cleaned_data.get("DELETE"):
                        continue

                    product = form_item.cleaned_data["product"]
                    quantity = form_item.cleaned_data["quantity"]
                    unit_price = form_item.cleaned_data["unit_price"]

                    stock_entry = Stock.objects.filter(product=product, store=store).first()
                    if not stock_entry or stock_entry.quantity < quantity:
                        messages.error(request, f"Not enough stock for {product.name}")
                        return render(request, 'dashboard/sale_receipt_form.html', {'form': form, 'formset': formset})

                    stock_entry.quantity -= quantity
                    stock_entry.save()

                    item = form_item.save(commit=False)
                    item.sale = sale
                    item.cost_price = stock_entry.cost_price or 0
                    item.save()

                    total += quantity * unit_price
                    cost_total += quantity * item.cost_price

                sale.total_amount = total
                sale.save(update_fields=["total_amount"])

                # ✅ Handle transaction
                bank_account = form.cleaned_data.get('bank_account')
                description = f"Sale Receipt - {sale.receipt_number}"

                revenue_txn = record_transaction_by_slug(
                    source_slug='sales-revenue',
                    destination_slug=bank_account.slug if bank_account else 'undeposited-funds',
                    amount=total,
                    description=description,
                    store=store
                )

                cogs_txn = record_transaction_by_slug(
                    source_slug='inventory-assets',
                    destination_slug='cost-of-goods-sold',
                    amount=cost_total,
                    description=f"COGS for {sale.receipt_number}",
                    store=store
                )

                sale.revenue_transaction = revenue_txn
                sale.cogs_transaction = cogs_txn
                sale.transaction = revenue_txn
                sale.save(update_fields=["revenue_transaction", "cogs_transaction", "transaction"])

                AuditLog.objects.create(
                    user=request.user,
                    action='sale',
                    description=f"{request.user.username} recorded a sale receipt for {sale.customer.name}",
                    store=store  # ✅ Add store for audit traceability
                )

                messages.success(request, f"Receipt created successfully. No: {sale.receipt_number}")
                return redirect('inventory:sale_receipt_create')

        except Exception as e:
            logger.error(f"❌ Sale receipt failed: {e}")
            messages.error(request, "Something went wrong while recording the receipt.")

    return render(request, 'dashboard/sale_receipt_form.html', {
        'form': form,
        'formset': formset,
    })


@login_required
def invoice_create(request):
    user = request.user

    if user.role not in ['sales', 'clerk', 'manager', 'admin'] and not user.is_superuser:
        return render(request, 'errors/permission_denied.html', status=403)

    form = InvoiceForm(request.POST or None, request=request)
    formset = SaleItemFormSet(request.POST or None, prefix="form")

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        try:
            with transaction.atomic():
                sale = form.save(commit=False)
                sale.sale_type = 'invoice'
                sale.sold_by = user
                sale.payment_status = 'unpaid'

                store = sale.store
                if not user.is_superuser and store not in user.stores.all():
                    return HttpResponse("Access Denied: You cannot create an invoice for this store.", status=403)

                sale.save()

                if not sale.receipt_number:
                    sale.receipt_number = f"INV-{sale.id:06d}"
                    sale.save(update_fields=["receipt_number"])

                total_sales = Decimal('0.00')
                total_cogs = Decimal('0.00')

                for form_item in formset:
                    if form_item.cleaned_data.get("DELETE"):
                        continue

                    product = form_item.cleaned_data["product"]
                    quantity = form_item.cleaned_data["quantity"]
                    unit_price = form_item.cleaned_data["unit_price"]

                    stock_entry = Stock.objects.filter(product=product, store=store).first()
                    if not stock_entry or stock_entry.quantity < quantity:
                        raise ValueError(f"Not enough stock for {product.name}")

                    stock_entry.quantity -= quantity
                    stock_entry.save(update_fields=["quantity"])

                    item = form_item.save(commit=False)
                    item.sale = sale
                    item.cost_price = stock_entry.cost_price or 0
                    item.save()

                    total_sales += quantity * unit_price
                    total_cogs += quantity * item.cost_price

                # 🧾 Update totals + balance
                sale.total_amount = total_sales
                sale.amount_paid = Decimal('0.00')
                sale.balance_due = total_sales
                sale.save(update_fields=["total_amount", "amount_paid", "balance_due"])

                # 💸 Record accounting entries
                revenue_txn = record_transaction_by_slug(
                    source_slug='sales-revenue',
                    destination_slug='accounts-receivable',
                    amount=total_sales,
                    store=store,
                    description=f"Invoice - {sale.receipt_number}"
                )

                cogs_txn = record_transaction_by_slug(
                    source_slug='inventory-assets',
                    destination_slug='cost-of-goods-sold',
                    amount=total_cogs,
                    store=store,
                    description=f"COGS for {sale.receipt_number}"
                )

                sale.revenue_transaction = revenue_txn
                sale.cogs_transaction = cogs_txn
                sale.transaction = revenue_txn
                sale.save(update_fields=["revenue_transaction", "cogs_transaction", "transaction"])

                # 🧾 Log audit entry
                AuditLog.objects.create(
                    user=user,
                    action='adjustment',
                    description=f"{user.username} created invoice {sale.receipt_number} for {sale.customer.name}",
                    store=store
                )

                messages.success(request, f"✅ Invoice No {sale.receipt_number} recorded.")
                return redirect('inventory:invoice_create')

        except Exception as e:
            logger.error(f"❌ Invoice creation failed: {e}")
            messages.error(request, f"Something went wrong: {e}")

    return render(request, 'dashboard/invoice_form.html', {
        'form': form,
        'formset': formset,
    })


from django.http import JsonResponse, HttpResponseForbidden

@login_required
def get_stock_quantity(request):
    product_id = request.GET.get('product_id')
    store_id = request.GET.get('store_id')

    # ✅ Restrict store access
    if not request.user.is_superuser and not request.user.stores.filter(id=store_id).exists():
        return HttpResponseForbidden("Access Denied: You do not have permission to view this store.")

    try:
        stock = Stock.objects.get(product_id=product_id, store_id=store_id)
        return JsonResponse({'quantity': stock.quantity})
    except Stock.DoesNotExist:
        return JsonResponse({'quantity': 0})

@login_required
def default_dashboard(request):
    return render(request, 'dashboard/default.html')


@login_required
def product_list(request):
    products = Product.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'dashboard/product_list.html', {'products': products})

def generate_sku():
    prefix = "PROD-"
    last = Product.objects.order_by('-id').first()
    next_id = (last.id + 1) if last else 1
    return f"{prefix}{next_id:03d}"  # PROD-001, PROD-002


@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductWithStockForm(request.POST, user=request.user)
        if form.is_valid():
            product = form.save(commit=False)

            # Generate SKU automatically
            last_product = Product.objects.order_by('-id').first()
            next_id = last_product.id + 1 if last_product else 1
            product.sku = f"PRD-{next_id:03d}"

            product.created_by = request.user
            product.save()

            # ✅ Get additional fields from form
            quantity = form.cleaned_data.get('starting_quantity') or 0
            cost_price = form.cleaned_data.get('cost_price') or 0
            store = form.cleaned_data.get('store')

            if quantity and store:
                # Record inventory and accounting
                txn = record_transaction_by_slug(
                    source_slug='opening-balance',
                    destination_slug='inventory-assets',
                    amount=quantity * cost_price,
                    description=f"Initial stock for {product.name}",
                    store=store
                )

                Stock.objects.create(
                    product=product,
                    store=store,
                    quantity=quantity,
                    cost_price=cost_price,
                    transaction=txn  # 🧾 Track for reversal
                )

            AuditLog.objects.create(
                user=request.user,
                action="create",
                description=f"Created product {product.name} ({product.sku})",
                store=store
            )

            messages.success(request, "✅ Product created successfully.")
            return redirect('inventory:product_list')
    else:
        form = ProductWithStockForm(user=request.user)

    return render(request, 'dashboard/product_form.html', {'form': form, 'product': None})

@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # 🔐 Optional: restrict by store if needed (e.g., manager can only edit products tied to their store)

    if request.method == 'POST':
        form = ProductWithStockForm(request.POST, instance=product, user=request.user)
        if form.is_valid():
            product = form.save(commit=False)
            product.updated_by = request.user
            product.save()

            AuditLog.objects.create(
                user=request.user,
                action="update",
                description=f"Updated product {product.name} ({product.sku})",
                store=None
            )

            messages.success(request, "✅ Product updated successfully.")
            return redirect('inventory:product_list')
    else:
        form = ProductWithStockForm(instance=product, user=request.user)

    return render(request, 'dashboard/product_form.html', {
        'form': form,
        'product': product
    })

@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # 🔒 Prevent deletion if product is referenced in transactions
    linked = any([
        SaleItem.objects.filter(product=product).exists(),
        Purchase.objects.filter(product=product).exists(),
        PurchaseOrderItem.objects.filter(product=product).exists()
    ])

    if linked:
        messages.error(request, f"❌ Cannot delete product '{product.name}' — it has related transactions.")
        return redirect('inventory:product_list')

    if request.method == 'POST':
        stock_entries = Stock.objects.filter(product=product)

        for stock in stock_entries:
            if stock.quantity > 0 and stock.transaction:
                reverse_transaction(
                    original_transaction_id=stock.transaction.id,
                    reason=f"Product '{product.name}' deleted"
                )

        stock_entries.delete()

        AuditLog.objects.create(
            user=request.user,
            action="delete",
            description=f"Deleted product '{product.name}' (SKU: {product.sku}) and reversed stock entries",
            store=None
        )

        product.delete()
        messages.success(request, f"✅ Product '{product.name}' deleted and stock reversed.")
        return redirect('inventory:product_list')

    return render(request, 'dashboard/product_confirm_delete.html', {'product': product})


from django.db.models import Q
from inventory.models import Product, Store
from collections import defaultdict


from collections import defaultdict

from collections import defaultdict
from django.http import HttpResponse
from django.db.models import Sum, F, Q, Case, When, Value, BooleanField


@login_required
def stock_list(request):
    user = request.user
    selected_store_id = request.GET.get("store")
    selected_product_id = request.GET.get("product")

    # 🔁 Base queryset with joins
    stocks = Stock.objects.select_related('store', 'product')
    products = Product.objects.all()

    # 🔐 Store access control
    if not user.is_superuser:
        allowed_store_ids = list(user.stores.values_list('id', flat=True))
        stores = Store.objects.filter(id__in=allowed_store_ids)

        if selected_store_id:
            if int(selected_store_id) not in allowed_store_ids:
                return HttpResponse("Access Denied", status=403)
            stocks = stocks.filter(store_id=selected_store_id)
        else:
            stocks = stocks.filter(store_id__in=allowed_store_ids)
    else:
        stores = Store.objects.all()
        if selected_store_id:
            stocks = stocks.filter(store_id=selected_store_id)

    if selected_product_id:
        stocks = stocks.filter(product_id=selected_product_id)

    # ✅ Annotate low stock flag
    stocks = stocks.annotate(
        low_stock=Case(
            When(quantity__lt=F('product__reorder_level'), then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        )
    )

    # 🔢 Total across products
    total_per_product = defaultdict(int)
    for stock in stocks:
        total_per_product[stock.product.id] += stock.quantity

    overall_total_stock = sum(total_per_product.values())

    return render(request, 'dashboard/stock_list.html', {
        'stocks': stocks,
        'stores': stores,
        'products': products,
        'selected_store': selected_store_id or "",
        'selected_product': selected_product_id or "",
        'total_per_product': total_per_product,
        'overall_total_stock': overall_total_stock,
    })



import random
import string

def generate_quote_number():
    from .models import Quotation
    while True:
        number = ''.join(random.choices(string.digits, k=6))
        if not Quotation.objects.filter(quote_number=number).exists():
            return number

from .forms import QuotationItemFormSet, QuotationForm

@login_required
def quotation_create(request):
    user = request.user

    # Limit stores based on role
    if user.is_superuser or user.role == 'admin':
        allowed_stores = Store.objects.all()
    else:
        allowed_stores = user.stores.all()

    if request.method == 'POST':
        form = QuotationForm(request.POST)
        form.fields['store'].queryset = allowed_stores  # 🔒 Reinforce validation
        formset = QuotationItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            quotation = form.save(commit=False)

            # 🔐 Double-check store is allowed
            if quotation.store not in allowed_stores:
                messages.error(request, "You don't have permission to use this store.")
                return redirect('inventory:quotation_create')

            quotation.created_by = user
            quotation.quote_number = generate_quote_number()
            quotation.save()

            formset.instance = quotation
            formset.save()

            messages.success(request, "Quotation created successfully.")
            return redirect('inventory:quotation_detail', quotation.id)
    else:
        form = QuotationForm()
        form.fields['store'].queryset = allowed_stores  # 🔒 Limit dropdown options
        formset = QuotationItemFormSet()

    return render(request, 'dashboard/quotation_form.html', {
        'form': form,
        'formset': formset,
    })

# from django.shortcuts import get_object_or_404

@login_required
def quotation_detail(request, pk):
    quotation = get_object_or_404(
        Quotation.objects.select_related('customer', 'store', 'created_by').prefetch_related('items__product'),
        pk=pk
    )
    return render(request, 'dashboard/quotation_detail.html', {
        'quotation': quotation
    })

# from django.contrib.auth.decorators import login_required
from .models import Quotation

@login_required
def quotation_list(request):
    # Superuser and admins see all, others see only their created ones
    if request.user.is_superuser or request.user.role == 'admin':
        quotations = Quotation.objects.select_related('customer', 'store').all()
    else:
        quotations = Quotation.objects.select_related('customer', 'store').filter(created_by=request.user)

    return render(request, 'dashboard/quotation_list.html', {
        'quotations': quotations
    })
# from weasyprint import HTML
# from django.template.loader import render_to_string
# from django.http import HttpResponse
# from .models import Quotation

@login_required
def quotation_pdf(request, pk):
    quotation = get_object_or_404(
        Quotation.objects.select_related('customer', 'store', 'created_by').prefetch_related('items__product'),
        pk=pk
    )

    company = quotation.store.company_profile if quotation.store and quotation.store.company_profile else CompanyProfile.objects.first()

    context = {
        'quotation': quotation,
        'items': quotation.items.all(),
        'company': company,
        'user': request.user
    }

    html = render_to_string('pdf/quotation_pdf.html', context)
    pdf = HTML(string=html, base_url=request.build_absolute_uri()).write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Quotation_{quotation.id}.pdf"'
    return response



@login_required
def stock_transfer_list_view(request):
    user = request.user

    if not (user.is_superuser or user.role == 'admin' or user.can_view_transfers):
        messages.error(request, "You do not have permission to view stock transfers.")
        return render(request, 'errors/permission_denied.html', status=403)

    transfers = StockTransfer.objects.select_related(
        'product', 'source_store', 'destination_store'
    ).order_by('-id')

    user_store_ids = list(request.user.stores.values_list('id', flat=True))

    return render(request, 'dashboard/stock_transfer_list.html', {
        'transfers': transfers,
        'user_store_ids': user_store_ids,
    })

# from django.views.decorators.http import require_POST

from accounting.services import record_transaction_by_slug

# from inventory.models import StockTransfer
# from accounting.models import AuditLog

@login_required
def stock_transfer_create(request):
    if not request.user.can_transfer_stock and not request.user.is_superuser:
        messages.error(request, "You do not have permission to transfer stock.")
        return render(request, 'errors/permission_denied.html', status=403)

    if request.method == 'POST':
        form = StockTransferForm(request.POST, request=request)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.status = 'requested'

            source_stock = Stock.objects.filter(
                product=transfer.product,
                store=transfer.source_store
            ).first()

            if not source_stock or source_stock.quantity < transfer.quantity:
                messages.error(request, "Insufficient stock to initiate transfer.")
                return redirect('inventory:stock_transfer_create')

            unit_cost = source_stock.cost_price or 0
            total_value = unit_cost * transfer.quantity

            txn = record_transaction_by_slug(
                source_slug='inventory-assets',
                destination_slug='transit-stock',
                amount=total_value,
                store=transfer.source_store,
                description=f"Transfer INIT #{transfer.id or 'NEW'}: {transfer.quantity} x {transfer.product.name} from {transfer.source_store.name}"
            )

            transfer.transfer_transaction = txn
            transfer.save()

            messages.success(request, 'Stock transfer request submitted and in transit.')
            return redirect('inventory:stock_transfer_list')
    else:
        form = StockTransferForm(request=request)

    return render(request, 'dashboard/stock_transfer.html', {'form': form})

@login_required
def transfer_slip_pdf(request, transfer_id):
    transfer = get_object_or_404(StockTransfer, id=transfer_id)

    company = transfer.source_store.company_profile if transfer.source_store else CompanyProfile.objects.first()

    context = {
        'transfer': transfer,
        'items': [{
            'product': transfer.product,
            'quantity': transfer.quantity
        }],
        'user': request.user,
        'date': timezone.now(),

        # 🏢 Company Info
        'company': company,

        # 📦 Transfer details
        'from_store': transfer.source_store,
        'to_store': transfer.destination_store,
        'created_by': transfer.created_by.get_full_name() if transfer.created_by else "N/A",
        'status': transfer.get_status_display() if hasattr(transfer, 'get_status_display') else transfer.status
    }

    template = get_template('pdf/transfer_slip.html')
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="TransferSlip_{transfer.id}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('We had errors <pre>' + html + '</pre>')
    return response


@require_POST
@login_required
def approve_transfer(request, transfer_id):
    transfer = get_object_or_404(StockTransfer, id=transfer_id)

    if not request.user.is_superuser and not (
        request.user.role == 'admin' or
        (request.user.role == 'manager' and transfer.destination_store in request.user.stores.all())
    ):
        return HttpResponseForbidden("You don't have permission to approve this transfer.")

    if transfer.status != 'requested':
        messages.warning(request, "This transfer has already been processed.")
        return redirect('inventory:stock_transfer_list')

    try:
        with transaction.atomic():
            source_stock = Stock.objects.filter(
                product=transfer.product,
                store=transfer.source_store
            ).first()

            if not source_stock or source_stock.quantity < transfer.quantity:
                messages.error(request, "Insufficient stock to approve transfer.")
                return redirect('inventory:stock_transfer_list')

            unit_cost = source_stock.cost_price or 0
            total_value = unit_cost * transfer.quantity

            # 1️⃣ Reduce quantity from source (already accounted)
            source_stock.quantity -= transfer.quantity
            source_stock.save()

            # 2️⃣ Add quantity to destination
            dest_stock, created = Stock.objects.get_or_create(
                product=transfer.product,
                store=transfer.destination_store,
                defaults={'quantity': 0, 'cost_price': unit_cost}
            )
            dest_stock.quantity += transfer.quantity
            dest_stock.save()

            # 3️⃣ Move value: Transit Stock → Inventory Assets (in receiving store)
            record_transaction_by_slug(
                source_slug='transit-stock',
                destination_slug='inventory-assets',
                amount=total_value,
                store=transfer.destination_store,
                description=f"Transfer COMPLETE #{transfer.id}: {transfer.quantity} x {transfer.product.name} received at {transfer.destination_store.name}"
            )

            # 4️⃣ Mark transfer approved
            transfer.status = 'approved'
            transfer.save()

            AuditLog.objects.create(
                user=request.user,
                action='transfer_approval',
                store=transfer.destination_store,
                description=f"{request.user.username} approved stock transfer #{transfer.id}"
            )

            messages.success(request, "Transfer approved and inventory updated.")
    except Exception as e:
        messages.error(request, f"Error approving transfer: {e}")

    return redirect('inventory:stock_transfer_list')

@require_POST
@login_required
def reject_transfer(request, transfer_id):
    transfer = get_object_or_404(StockTransfer, id=transfer_id)

    if not request.user.is_superuser and not (
        request.user.role == 'admin' or
        (request.user.role == 'manager' and transfer.destination_store in request.user.stores.all())
    ):
        return HttpResponseForbidden("You don't have permission to reject this transfer.")

    if transfer.status != 'requested':
        messages.warning(request, "This transfer has already been processed.")
        return redirect('inventory:stock_transfer_list')

    try:
        with transaction.atomic():
            # 1️⃣ Reverse initial accounting entry if exists
            if transfer.transfer_transaction:
                reverse_transaction(
                    original_transaction_id=transfer.transfer_transaction.id,
                    reason=f"Rejected stock transfer #{transfer.id}"
                )

            # 2️⃣ Update transfer status
            transfer.status = 'rejected'
            transfer.save()

            AuditLog.objects.create(
                user=request.user,
                action='transfer_rejection',
                description=f"{request.user.username} rejected stock transfer #{transfer.id}"
            )

            messages.success(request, "Transfer rejected and reversed.")
    except Exception as e:
        messages.error(request, f"Error rejecting transfer: {e}")

    return redirect('inventory:stock_transfer_list')

# inventory/views.py

# from django.contrib.auth.decorators import login_required
# from django.shortcuts import render

@login_required
def inventory_aging_report(request):
    from inventory.utils import get_inventory_aging_data
    from datetime import datetime

    store_id = request.GET.get('store')
    status = request.GET.get('status')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    store = Store.objects.filter(id=store_id).first() if store_id else None

    # Parse dates
    start = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
    end = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
    status_choices = ['Fresh', 'Stale', 'Critical', 'No Sales']
    

    report = get_inventory_aging_data(
        user=request.user,
        store=store,
        start_date=start,
        end_date=end,
        status_filter=status
    )

    # Dropdown store list
    stores = Store.objects.all() if request.user.is_superuser else request.user.stores.all()
    print("🧾 AGING REPORT ENTRIES:", len(report))


    return render(request, 'dashboard/inventory_aging.html', {
        'report': report,
        'stores': stores,
        'selected_store': store_id,
        'selected_status': status,
        'start_date': start_date,
        'end_date': end_date,
        'status_choices': status_choices,  # ✅ add this

    })

@login_required
def stock_adjustment_create(request):
    user = request.user

    if not user.can_adjust_stock and not user.is_superuser:
        messages.error(request, "You do not have permission to adjust stock.")
        return render(request, 'errors/permission_denied.html', status=403)

    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)

        if form.is_valid():
            store = form.cleaned_data['store']
            product = form.cleaned_data['product']
            quantity = form.cleaned_data['quantity']
            reason = form.cleaned_data['reason']
            adjustment_type = form.cleaned_data['adjustment_type']

            # ✅ Restrict to assigned stores
            if not user.is_superuser and not user.stores.filter(id=store.id).exists():
                return HttpResponseForbidden("You can only adjust stock for stores assigned to you.")

            stock_entry = Stock.objects.filter(product=product, store=store).first()
            if not stock_entry:
                messages.error(request, "No stock entry for this product in the selected store.")
                return redirect('inventory:stock_adjustment_create')

            unit_price = stock_entry.cost_price or 0  # ✅ Define unit price from stock
            current_qty = stock_entry.quantity

            if adjustment_type == 'subtract' and current_qty < quantity:
                messages.error(request, "Insufficient stock in the selected store.")
                return redirect('inventory:stock_adjustment_create')

            adjusted_quantity = abs(quantity) if adjustment_type == 'add' else -abs(quantity)
            accounting_amount = abs(adjusted_quantity) * unit_price

            try:
                with transaction.atomic():
                    # ✅ Apply Adjustment
                    StockAdjustment.objects.create(
                        store=store,
                        product=product,
                        quantity=adjusted_quantity,
                        reason=reason,
                        adjusted_by=user
                    )

                    # ✅ Update inventory
                    stock_entry.quantity += adjusted_quantity
                    stock_entry.save(update_fields=["quantity"])

                    product.total_quantity += adjusted_quantity
                    product.save(update_fields=["total_quantity"])

                    # ✅ Accounting Entries
                    from accounting.services import record_transaction_by_slug

                    if accounting_amount > 0:
                        if adjustment_type == 'add':
                            record_transaction_by_slug(
                                source_slug='inventory-adjustment-gain',
                                destination_slug='inventory-assets',
                                amount=accounting_amount,
                                store=store,
                                description=f"Stock gain adjustment for {product.name}"
                            )
                        elif adjustment_type == 'subtract':
                            record_transaction_by_slug(
                                source_slug='inventory-assets',
                                destination_slug='inventory-adjustment-loss',
                                amount=accounting_amount,
                                store=store,
                                description=f"Stock loss adjustment for {product.name}"
                            )

                    # ✅ Audit log
                    AuditLog.objects.create(
                        user=user,
                        store=store,
                        action='adjustment',
                        description=f"{user.username} adjusted {product.name} in {store.name} by {adjusted_quantity} units. Reason: {reason}"
                    )

                    messages.success(request, "Stock adjustment successfully recorded!")
                    return redirect('inventory:stock_adjustment_create')

            except Exception as e:
                messages.error(request, f"An error occurred: {e}")
                return redirect('inventory:stock_adjustment_create')

    else:
        form = StockAdjustmentForm()
        form.fields['product'].queryset = Product.objects.all()
        form.fields['store'].queryset = Store.objects.all() if user.is_superuser else user.stores.all()

    return render(request, 'dashboard/stock_adjustment_form.html', {'form': form})

from django.http import JsonResponse
from inventory.models import Product, PurchaseOrderItem

@login_required
def get_product_prices(request):
    product_id = request.GET.get('product_id')
    data = {}

    if product_id:
        try:
            latest_item = PurchaseOrderItem.objects.filter(product_id=product_id).latest('id')
            data['unit_price'] = float(latest_item.unit_price)
            data['expected_sales_price'] = float(getattr(latest_item, 'expected_sales_price', 0))
        except PurchaseOrderItem.DoesNotExist:
            product = Product.objects.filter(id=product_id).first()
            if product:
                data['unit_price'] = 0
                data['expected_sales_price'] = 0

    return JsonResponse(data)

@login_required
def create_purchase_order(request):
    ItemFormSet = modelformset_factory(PurchaseOrderItem, form=PurchaseOrderItemForm, extra=1, can_delete=True)

    if request.method == 'POST':
        item_formset = ItemFormSet(request.POST, queryset=PurchaseOrderItem.objects.none())
        supplier_name = request.POST.get('supplier')

        if item_formset.is_valid() and supplier_name:
            supplier, _ = Supplier.objects.get_or_create(
                name__iexact=supplier_name.strip(),
                defaults={"name": supplier_name}
            )

            po = PurchaseOrder(supplier=supplier, created_by=request.user)
            po.save()

            for form in item_formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    item = form.save(commit=False)
                    item.purchase_order = po
                    item.save()

            messages.success(request, "Purchase Order created successfully.")
            return redirect('inventory:purchase_order_list')

    else:
        item_formset = ItemFormSet(queryset=PurchaseOrderItem.objects.none())

    stores = Store.objects.all() if request.user.is_superuser else request.user.stores.all()

    return render(request, 'dashboard/purchase_order_form.html', {
        'item_formset': item_formset,
        'suppliers': Supplier.objects.all(),
        'stores': stores,
    })

@require_POST
@login_required
def purchase_order_delete_view(request, pk):
    if not request.user.is_superuser and request.user.role != 'manager':
        return HttpResponseForbidden("Only managers or admins can delete purchase orders.")

    po = get_object_or_404(PurchaseOrder, pk=pk)

    # ✅ Check that user has access to this store
    if not request.user.is_superuser and po.store not in request.user.stores.all():
        return HttpResponseForbidden("You cannot delete a purchase order from a store you do not manage.")

    if po.status == 'received':
        messages.error(request, "Cannot delete a received purchase order.")
        return redirect('inventory:purchase_order_list')

    try:
        with transaction.atomic():
            po.delete()
            messages.success(request, f"Purchase Order PO-{pk} deleted successfully.")
    except Exception as e:
        messages.error(request, f"Error deleting purchase order: {e}")

    return redirect('inventory:purchase_order_list')

@login_required
def stock_adjustment_list(request):
    return HttpResponse("Stock Adjustment List Coming Soon")
