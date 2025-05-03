from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.http import HttpResponse
from inventory.models import StockTransfer,Supplier
from inventory.forms import StockTransferForm
from .forms import StockAdjustmentForm, ProductForm
from .models import Product, Store, StockAdjustment
from django.core.paginator import Paginator
from .forms import PurchaseForm
from .models import Purchase
from .forms import SaleForm, SaleItemFormSet
from django.http import JsonResponse
from .models import Stock
from django.db.models import Q
from users.models import User
import csv
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.utils.safestring import mark_safe
from .forms import PurchaseOrderForm, PurchaseOrderItem, PurchaseOrderItemForm, PurchaseOrder
from django.forms import modelformset_factory
from .forms import SupplierForm
from .models import CompanyProfile
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
from .models import SaleReturn, SaleReturnItem
from django.views.decorators.http import require_POST
from accounting.services import record_transaction
import logging
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import SaleForm, SaleItemFormSet
from .models import Sale, SaleItem, Stock, AuditLog
from .models import Sale
from django.core.paginator import Paginator
from django.db.models import Sum
from .forms import InvoiceForm





@login_required
def customer_create(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer added successfully.")
            return redirect('inventory:sale_create')  # Or wherever you want to redirect
    else:
        form = CustomerForm()
    return render(request, 'dashboard/customer_form.html', {'form': form})

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


@login_required
def export_po_receipt_pdf(request, po_id):
    po = get_object_or_404(PurchaseOrder.objects.prefetch_related('items__product', 'supplier'), pk=po_id)

    # Calculate total
    total = sum([item.subtotal for item in po.items.all()])

    # Get company info from the DB
    company = CompanyProfile.objects.first()

    context = {
        'po': po,
        'total': total,
        'store': request.user.store if not request.user.is_superuser else None,
        'received_by': request.user,
        'company': company,
    }

    html_template = get_template('pdf/po_receipt.html')
    html_content = html_template.render(context)

    pdf_file = HTML(string=html_content, base_url=request.build_absolute_uri()).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="PO-{po.id}-receipt.pdf"'
    return response

@login_required
def inventory_report_view(request):
    role = getattr(request.user, 'role', '').lower()
    store = getattr(request.user, 'store', None)

    stocks = Stock.objects.select_related('product', 'store')

    # Restrict staff to their own store
    if role == 'staff' and store:
        stocks = stocks.filter(store=store)

    # Filters
    product_id = request.GET.get('product')
    store_id = request.GET.get('store')

    if product_id:
        stocks = stocks.filter(product_id=product_id)

    if store_id and role != 'staff':
        stocks = stocks.filter(store_id=store_id)

    products = Product.objects.all()
    stores = Store.objects.all()

    return render(request, 'dashboard/inventory_report.html', {
        'stocks': stocks,
        'products': products,
        'stores': stores,
        'selected_product': product_id,
        'selected_store': store_id
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

@login_required
def export_inventory_pdf(request):
    role = getattr(request.user, 'role', '').lower()
    store = getattr(request.user, 'store', None)

    stocks = Stock.objects.select_related('product', 'store')
    if role == 'staff' and store:
        stocks = stocks.filter(store=store)

    # Clean filter inputs
    product_id = request.GET.get('product')
    store_id = request.GET.get('store')

    if product_id and product_id.isdigit():
        stocks = stocks.filter(product_id=int(product_id))

    if store_id and store_id.isdigit() and role != 'staff':
        stocks = stocks.filter(store_id=int(store_id))

    context = {
        'stocks': stocks,
        'user': request.user,
    }

    template = get_template('pdf/inventory_report_pdf.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="inventory_report.pdf"'
    pisa.CreatePDF(html, dest=response)
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



@login_required
def export_po_pdf(request, po_id):
    po = get_object_or_404(PurchaseOrder, pk=po_id)

    if not request.user.is_superuser and request.user.role != 'admin' and request.user != po.created_by:
        return render(request, 'errors/permission_denied.html', status=403)

    total = sum(item.subtotal for item in po.items.all())
    company = CompanyProfile.objects.first()

    template = get_template('dashboard/purchase_order_pdf.html')
    html = template.render({'po': po, 'total': total, 'company': company})

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="PO-{po.id}.pdf"'

    pisa.CreatePDF(html, dest=response)
    return response


@login_required
def purchase_order_detail(request, po_id):
    po = get_object_or_404(
        PurchaseOrder.objects.select_related('supplier', 'created_by').prefetch_related('items__product'),
        pk=po_id
    )

    if not request.user.is_superuser and request.user.role != 'admin' and request.user != po.created_by:
        messages.error(request, "You're not authorized to view this Purchase Order.")
        return render(request, 'errors/permission_denied.html', status=403)

    # ✅ Calculate total from item subtotals
    total = sum(item.subtotal for item in po.items.all())

    return render(request, 'dashboard/purchase_order_detail.html', {
        'po': po,
        'total': total
    })



@login_required
def receive_purchase_order(request, po_id):
    po = get_object_or_404(PurchaseOrder, pk=po_id)

    if po.status == 'received':
        messages.warning(request, "This PO has already been marked as received.")
        return redirect('inventory:purchase_order_detail', po_id=po.id)

    if request.method == 'POST':
        if request.user.is_superuser or request.user.role == 'admin':
            store_id = request.POST.get('store')
            store = get_object_or_404(Store, id=store_id)
        else:
            store = request.user.store

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

                po.status = 'received'
                po.save()

                AuditLog.objects.create(
                    user=request.user,
                    action='adjustment',
                    description=f"{request.user.username} received PO-{po.id} and updated stock at {store.name}."
                )

                # ✅ Record slug-based accounting transaction
                from accounting.services import record_transaction_by_slug
                record_transaction_by_slug(
                    source_slug="accounts-payable",
                    destination_slug="inventory-assets",
                    amount=total_value,
                    description=f"PO-{po.id} Goods Received"
                )

                messages.success(request, "Purchase Order received and accounting recorded.")
                return redirect('inventory:purchase_order_detail', po_id=po.id)

        except Exception as e:
            logger.error(f"❌ PO receiving failed: {e}")
            messages.error(request, f"An error occurred: {e}")

    stores = Store.objects.all() if request.user.is_superuser or request.user.role == 'admin' else None
    return render(request, 'dashboard/receive_purchase_order.html', {'po': po, 'stores': stores})

@login_required
def purchase_order_list(request):
    purchase_orders = PurchaseOrder.objects.select_related('supplier', 'created_by').order_by('-date')

    supplier_id = request.GET.get('supplier')
    status = request.GET.get('status')
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')

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
        with transaction.atomic():
            # ✅ Reverse the accounting entry if transaction exists
            if sale.transaction:
                from accounting.services import reverse_transaction
                reverse_transaction(sale.transaction.id, reason=f"Sale Reversal: RCPT-{sale.receipt_number}")

            # ✅ Restore stock
            for item in sale.items.all():
                stock, _ = Stock.objects.get_or_create(product=item.product, store=sale.store)
                stock.quantity += item.quantity
                stock.save()

            sale.delete()
            messages.success(request, "Sale deleted, stock restored, and accounting reversed.")
            return redirect('inventory:sale_list')

    return render(request, 'dashboard/confirm_delete.html', {'object': sale, 'type': 'Sale'})


@login_required
def export_sales_pdf(request):
    sales = Sale.objects.select_related('product', 'store', 'sold_by').order_by('-sale_date')

    product = request.GET.get('product')
    store = request.GET.get('store')
    sold_by = request.GET.get('sold_by')
    start = request.GET.get('start')
    end = request.GET.get('end')

    filters = {}

    if not request.user.is_superuser and request.user.role != 'admin':
        sales = sales.filter(store=request.user.store)

    if product:
        sales = sales.filter(product_id=product)
        filters['product'] = Product.objects.filter(id=product).first()
    if store:
        sales = sales.filter(store_id=store)
        filters['store'] = Store.objects.filter(id=store).first()
    if sold_by:
        sales = sales.filter(sold_by_id=sold_by)
        filters['user'] = User.objects.filter(id=sold_by).first()
    if start and end:
        sales = sales.filter(sale_date__range=[start, end])
        filters['start'] = start
        filters['end'] = end

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


@login_required
def export_purchase_orders_pdf(request):
    orders = filter_purchase_orders(request)

    context = {
        'orders': orders,
        'user': request.user,
    }
    template = get_template('pdf/purchase_orders_report_pdf.html')
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="purchase_orders_{now().strftime("%Y%m%d")}.pdf"'
    pisa.CreatePDF(html, dest=response)
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


@login_required
def purchase_create(request):
    if not request.user.is_superuser and request.user.role != 'manager':
        return render(request, 'errors/permission_denied.html', status=403)

    if request.method == 'POST':
        form = PurchaseForm(request.POST, request=request)
        if form.is_valid():
            purchase = form.save(commit=False)
            purchase.purchased_by = request.user
            purchase.save()

            # Update stock
            stock, created = Stock.objects.get_or_create(
                product=purchase.product,
                store=purchase.store,
                defaults={'quantity': 0}
            )
            stock.quantity += purchase.quantity
            stock.save()

            # Audit
            AuditLog.objects.create(
                user=request.user,
                action='adjustment',
                description=f"{request.user.username} purchased {purchase.quantity} of {purchase.product.name} for {purchase.store.name}"
            )

            messages.success(request, "Purchase recorded and stock updated.")
            return redirect('inventory:purchase_create')
    else:
        form = PurchaseForm(request=request)

    return render(request, 'dashboard/purchase_form.html', {'form': form})


@login_required
def export_sales_csv(request):
    sales = Sale.objects.select_related('product', 'store', 'sold_by').order_by('-sale_date')

    # Apply same filters as sale_list_view
    if not request.user.is_superuser and request.user.role != 'admin':
        sales = sales.filter(store=request.user.store)

    if product_id := request.GET.get('product'):
        sales = sales.filter(product_id=product_id)
    if store_id := request.GET.get('store'):
        sales = sales.filter(store_id=store_id)
    if sold_by_id := request.GET.get('sold_by'):
        sales = sales.filter(sold_by_id=sold_by_id)
    if request.GET.get('start') and request.GET.get('end'):
        sales = sales.filter(sale_date__range=[request.GET['start'], request.GET['end']])

    # Create CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Product', 'Quantity', 'Store', 'Sold By', 'Date'])

    for sale in sales:
        writer.writerow([
            sale.product.name,
            sale.quantity,
            sale.store.name,
            sale.sold_by.username if sale.sold_by else "Unknown",
            sale.sale_date.strftime("%Y-%m-%d %H:%M")
        ])

    return response

@login_required
def audit_log_list_view(request):
    if not request.user.is_superuser and request.user.role != 'manager':
        return render(request, 'errors/permission_denied.html', status=403)

    logs = AuditLog.objects.select_related('user').order_by('-timestamp')
    paginator = Paginator(logs, 25)  # 25 logs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'dashboard/audit_log_list.html', {'page_obj': page_obj})


@login_required
def sale_return_view(request, sale_id):
    sale = get_object_or_404(Sale, pk=sale_id)

    if request.method == 'POST':
        form = SaleReturnForm(request.POST)
        formset = SaleReturnItemFormSet(request.POST)

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
                        # Update stock
                        stock = Stock.objects.get(product=sale_item.product, store=sale.store)
                        stock.quantity += return_qty
                        stock.save()

                        return_item.sale_return = sale_return
                        return_item.save()

                        total += return_qty * sale_item.unit_price

                sale_return.total_refunded = total
                sale_return.save()

                messages.success(request, "Return processed successfully.")
                return redirect('inventory:sale_detail', pk=sale_id)

    else:
        form = SaleReturnForm()
        formset = SaleReturnItemFormSet(
            queryset=SaleReturnItem.objects.none(),
            initial=[
                {'sale_item': item.id, 'quantity_returned': 0}
                for item in sale.items.all()
            ],
            prefix="return"
        )

        # Restrict the formset's sale_item queryset to sale's items only
        for subform in formset.forms:
            subform.fields['sale_item'].queryset = sale.items.all()
        sale_items_dict = {str(item.id): item for item in sale.items.all()}


    return render(request, 'dashboard/sale_return_form.html', {
    'form': form,
    'formset': formset,
    'sale': sale,
    'sale_items_dict': sale_items_dict,
})


@login_required
def sale_list_view(request):
    sales = Sale.objects.select_related('customer', 'store', 'sold_by').prefetch_related('items__product')

    # Filters
    product_id = request.GET.get('product')
    store_id = request.GET.get('store')
    sold_by_id = request.GET.get('sold_by')
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    query = request.GET.get('q')

    # Role-based restriction
    if not request.user.is_superuser and request.user.role != 'admin':
        sales = sales.filter(store=request.user.store)

    if query:
        sales = sales.filter(receipt_number__icontains=query)
    if product_id:
        sales = sales.filter(items__product_id=product_id)
    if store_id:
        sales = sales.filter(store_id=store_id)
    if sold_by_id:
        sales = sales.filter(sold_by_id=sold_by_id)
    if start_date and end_date:
        sales = sales.filter(sale_date__range=[start_date, end_date])

    # ✅ Now calculate revenue based on the filtered queryset
    total_revenue = sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_sales_count = sales.count()


    paginator = Paginator(sales.distinct(), 20)
    page = request.GET.get('page')
    sales_page = paginator.get_page(page)

    context = {
        'sales': sales_page,
        'products': Product.objects.all(),
        'stores': Store.objects.all(),
        'users': User.objects.all(),
        'total_revenue': total_revenue,
        'total_sales_count': total_sales_count,  # 👈 added

    }
    

    return render(request, 'dashboard/sale_list.html', context)


@require_POST
@login_required
def sale_delete_view(request, pk):
    if not request.user.is_superuser and request.user.role != 'manager':
        return HttpResponseForbidden("You are not allowed to delete sales.")
    
    sale = get_object_or_404(Sale, pk=pk)
    sale.delete()
    messages.success(request, f"Sale {pk} deleted successfully.")
    return redirect('inventory:sale_list')

@login_required
def sale_receipt_pdf(request, sale_id):
    sale = get_object_or_404(Sale.objects.prefetch_related('items__product'), pk=sale_id)

    company = CompanyProfile.objects.first()

    # Build logo URL using absolute media path
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

    return render(request, 'dashboard/sale_detail.html', {
        'sale': sale,
        'items': items
    })


@login_required
def admin_dashboard(request):
    total_products = Product.objects.count()
    total_stock = Stock.objects.aggregate(total=models.Sum('quantity'))['total'] or 0

    today = now().date()
    sales_today = Sale.objects.filter(sale_date__date=today).count()

    start_of_week = today - timedelta(days=today.weekday())
    sales_this_week = Sale.objects.filter(sale_date__date__gte=start_of_week).count()

    low_stock_threshold = 10  # or make this configurable later
    low_stock_products = Product.objects.filter(total_quantity__lt=low_stock_threshold)

    context = {
        'total_products': total_products,
        'total_stock': total_stock,
        'sales_today': sales_today,
        'sales_this_week': sales_this_week,
        'low_stock_products': low_stock_products,
    }

    return render(request, 'dashboard/admin.html', context)




logger = logging.getLogger(__name__)

# inventory/views.py

from accounting.services import record_transaction, reverse_transaction

from accounting.services import record_transaction_by_slug

@login_required
def sale_receipt_create(request):
    if request.user.role not in ['sales', 'clerk', 'manager', 'admin'] and not request.user.is_superuser:
        return render(request, 'errors/permission_denied.html', status=403)

    from .forms import SaleReceiptForm
    form = SaleReceiptForm(request.POST or None, request=request)
    formset = SaleItemFormSet(request.POST or None, prefix="form")

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        try:
            with transaction.atomic():
                sale = form.save(commit=False)
                sale.sold_by = request.user
                sale.sale_type = 'receipt'
                sale.payment_status = 'paid'
                sale.save()

                if not sale.receipt_number:
                    sale.receipt_number = f"RCPT-{sale.id:06d}"
                    sale.save(update_fields=["receipt_number"])

                total, cost_total = 0, 0
                for form_item in formset:
                    if form_item.cleaned_data.get("DELETE"):
                        continue

                    product = form_item.cleaned_data.get("product")
                    quantity = form_item.cleaned_data.get("quantity")
                    unit_price = form_item.cleaned_data.get("unit_price")
                    store = sale.store

                    stock_entry = Stock.objects.filter(product=product, store=store).first()
                    if not stock_entry or stock_entry.quantity < quantity:
                        messages.error(request, f"Not enough stock for {product.name}")
                        return render(request, 'dashboard/sale_receipt_form.html', {'form': form, 'formset': formset})

                    stock_entry.quantity -= quantity
                    stock_entry.save()

                    item = form_item.save(commit=False)
                    item.sale = sale
                    item.cost_price = stock_entry.cost_price if stock_entry.cost_price is not None else 0
                    item.save()

                    total += quantity * unit_price
                    cost_total += quantity * item.cost_price

                sale.total_amount = total
                sale.save(update_fields=["total_amount"])

                bank_account = form.cleaned_data.get('bank_account')
                description = f"Sale Receipt - {sale.receipt_number}"

                print(f"✅ Recording Revenue Transaction: {total} from Sales Revenue to {'bank account' if bank_account else 'Undeposited Funds'}")
                txn = record_transaction_by_slug(
                    source_slug='sales-revenue',
                    destination_slug=bank_account.slug if bank_account else 'undeposited-funds',
                    amount=total,
                    description=description
                )

                print(f"🔍 COGS Amount: {cost_total}")
                print("👉 Recording COGS transaction now...")
                record_transaction_by_slug(
                    source_slug='inventory-assets',
                    destination_slug='cost-of-goods-sold',
                    amount=cost_total,
                    description=f"COGS for {sale.receipt_number}"
                )

                if txn:
                    sale.transaction = txn
                    sale.save(update_fields=["transaction"])

                AuditLog.objects.create(
                    user=request.user,
                    action='sale',
                    description=f"{request.user.username} recorded a sale receipt for {sale.customer.name}"
                )

                messages.success(request, f"Receipt created successfully. No: {sale.receipt_number}")
                return redirect('inventory:sale_receipt_create')

        except Exception as e:
            logger.error(f"❌ Sale receipt failed: {e}")
            messages.error(request, "Something went wrong while recording the receipt.")

    return render(request, 'dashboard/sale_receipt_form.html', {'form': form, 'formset': formset})

@login_required
def invoice_create(request):
    if request.user.role not in ['sales', 'clerk', 'manager', 'admin'] and not request.user.is_superuser:
        return render(request, 'errors/permission_denied.html', status=403)

    form = InvoiceForm(request.POST or None, request=request)
    formset = SaleItemFormSet(request.POST or None, prefix="form")

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        try:
            with transaction.atomic():
                sale = form.save(commit=False)
                sale.sale_type = 'invoice'
                sale.sold_by = request.user
                sale.payment_status = 'unpaid'
                sale.save()

                if not sale.receipt_number:
                    sale.receipt_number = f"INV-{sale.id:06d}"
                    sale.save(update_fields=["receipt_number"])

                total = 0
                cost_total = 0
                store = sale.store

                for form_item in formset:
                    if form_item.cleaned_data.get("DELETE"):
                        continue

                    product = form_item.cleaned_data.get("product")
                    quantity = form_item.cleaned_data.get("quantity")
                    unit_price = form_item.cleaned_data.get("unit_price")

                    stock_entry = Stock.objects.filter(product=product, store=store).first()
                    if not stock_entry or stock_entry.quantity < quantity:
                        messages.error(request, f"Not enough stock for {product.name}")
                        return render(request, 'dashboard/invoice_form.html', {'form': form, 'formset': formset})

                    stock_entry.quantity -= quantity
                    stock_entry.save()

                    item = form_item.save(commit=False)
                    item.sale = sale
                    item.cost_price = getattr(stock_entry, 'cost_price', 0) or 0
                    item.save()

                    total += quantity * unit_price
                    cost_total += quantity * item.cost_price

                sale.total_amount = total
                sale.save(update_fields=["total_amount"])

                # ✅ ACCOUNTING TRANSACTIONS
                from accounting.services import record_transaction_by_slug

                # Sales Revenue (credit) → Accounts Receivable (debit)
                txn = record_transaction_by_slug(
                    source_slug='sales-revenue',
                    destination_slug='accounts-receivable',
                    amount=total,
                    description=f"Invoice - {sale.receipt_number}"
                )

                # Inventory Asset (credit) → COGS (debit)
                record_transaction_by_slug(
                    source_slug='inventory-assets',
                    destination_slug='cost-of-goods-sold',
                    amount=cost_total,
                    description=f"COGS for {sale.receipt_number}"
                )

                sale.transaction = txn
                sale.save(update_fields=["transaction"])

                AuditLog.objects.create(
                    user=request.user,
                    action='adjustment',
                    description=f"{request.user.username} created invoice {sale.receipt_number} for {sale.customer.name}"
                )

                messages.success(request, f"Invoice recorded successfully. Invoice No: {sale.receipt_number}")
                return redirect('inventory:invoice_create')

        except Exception as e:
            logger.error(f"❌ Invoice creation failed: {e}")
            messages.error(request, "Something went wrong while saving the invoice.")

    return render(request, 'dashboard/invoice_form.html', {
        'form': form,
        'formset': formset
    })


@login_required
def get_stock_quantity(request):
    product_id = request.GET.get('product_id')
    store_id = request.GET.get('store_id')

    try:
        stock = Stock.objects.get(product_id=product_id, store_id=store_id)
        return JsonResponse({'quantity': stock.quantity})
    except Stock.DoesNotExist:
        return JsonResponse({'quantity': 0})




# from .models import Product, Stock, Sale, Store, PurchaseOrder
# from django.utils.timezone import now

@login_required
def manager_dashboard(request):
    user_store = getattr(request.user, 'store', None)

    # If user has no assigned store, return empty or warning
    if not user_store:
        messages.warning(request, "You are not assigned to a store.")
        return render(request, 'dashboard/default.html')

    # Get stock and sales filtered to user's store
    store_stock = Stock.objects.filter(store=user_store)
    store_sales = Sale.objects.filter(store=user_store)
    recent_purchase_orders = PurchaseOrder.objects.filter(created_by=request.user).order_by('-date')[:5]

    total_products = Product.objects.count()
    total_sales_today = store_sales.filter(sale_date__date=now().date()).count()

    return render(request, 'dashboard/manager.html', {
        'store': user_store,
        'store_stock': store_stock,
        'store_sales': store_sales,
        'recent_purchase_orders': recent_purchase_orders,
        'total_products': total_products,
        'total_sales_today': total_sales_today,
    })


from .models import Sale

@login_required
def store_dashboard(request):
    user_store = getattr(request.user, 'store', None)

    if not user_store:
        messages.warning(request, "You are not assigned to a store.")
        return render(request, 'dashboard/default.html')

    stock = Stock.objects.filter(store=user_store).select_related('product')
    sales = Sale.objects.filter(store=user_store).order_by('-sale_date')[:10]

    return render(request, 'dashboard/staff.html', {
        'store': user_store,
        'stock': stock,
        'sales': sales,
    })


@login_required
def inventory_dashboard(request):
    user_store = getattr(request.user, 'store', None)

    if not user_store:
        messages.warning(request, "No store assigned to your account.")
        return render(request, 'dashboard/default.html')

    stocks = Stock.objects.filter(store=user_store).select_related('product')

    return render(request, 'dashboard/inventory.html', {
        'stocks': stocks,
        'store': user_store,
    })


from .models import Product, Sale
from django.utils.timezone import now

@login_required
def sales_dashboard(request):
    today = now().date()
    today_sales = Sale.objects.filter(sale_date__date=today, sold_by=request.user)

    return render(request, 'dashboard/sales.html', {
        'sales': today_sales,
    })



@login_required
def default_dashboard(request):
    return render(request, 'dashboard/default.html')


@login_required
def product_list(request):
    products = Product.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'dashboard/product_list.html', {'products': products})


@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('inventory:product_list')
    else:
        form = ProductForm()
    return render(request, 'dashboard/product_form.html', {'form': form, 'product': None})


@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('inventory:product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'dashboard/product_form.html', {'form': form, 'product': product})


@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully.')
        return redirect('inventory:product_list')
    return render(request, 'dashboard/product_confirm_delete.html', {'product': product})


@login_required
def stock_list(request):
    stocks = Stock.objects.select_related('store', 'product')
    return render(request, 'dashboard/stock_list.html', {'stocks': stocks})


@login_required
def stock_transfer_list_view(request):
    if not getattr(request.user, 'can_view_transfers', False):
        messages.error(request, "You do not have permission to view stock transfers.")
        return render(request, 'errors/permission_denied.html', status=403)

    transfers = StockTransfer.objects.select_related(
        'product', 'source_store', 'destination_store'
    ).order_by('-id')

    return render(request, 'dashboard/stock_transfer_list.html', {'transfers': transfers})


@login_required
def stock_transfer_view(request):
    if not request.user.can_transfer_stock and not request.user.is_superuser:
        messages.error(request, "You do not have permission to transfer stock.")
        return render(request, 'errors/permission_denied.html', status=403)

    if request.method == 'POST':
        form = StockTransferForm(request.POST, request=request)
        if form.is_valid():
            product = form.cleaned_data['product']
            source_store = form.cleaned_data['source_store']
            destination_store = form.cleaned_data['destination_store']
            quantity = form.cleaned_data['quantity']

            source_stock = Stock.objects.filter(product=product, store=source_store).first()
            destination_stock = Stock.objects.filter(product=product, store=destination_store).first()

            if not source_stock:
                messages.error(request, 'Product not found in source store.')
                return render(request, 'dashboard/stock_transfer.html', {'form': form})

            if source_stock.quantity < quantity:
                messages.error(request, 'Insufficient stock in source store.')
                return render(request, 'dashboard/stock_transfer.html', {'form': form})

            try:
                with transaction.atomic():
                    source_stock.quantity -= quantity
                    source_stock.save()

                    if destination_stock:
                        destination_stock.quantity += quantity
                        destination_stock.save()
                    else:
                        Stock.objects.create(
                        product=product,
                        store=destination_store,
                        quantity=quantity
                    )
                        
                    StockTransfer.objects.create(
                        product=product,
                        source_store=source_store,
                        destination_store=destination_store,
                        quantity=quantity
                    )
                    AuditLog.objects.create(
                        user=request.user,
                        action='transfer',
                        description=f"{request.user.username} transferred {quantity} of {product.name} from {source_store.name} to {destination_store.name}"
                    )

                messages.success(request, 'Stock transferred successfully!')
                return redirect('inventory:stock_transfer')
            except Exception as e:
                messages.error(request, f"Error during transfer: {e}")
           
    else:
        form = StockTransferForm(request=request)

    return render(request, 'dashboard/stock_transfer.html', {'form': form})


@login_required
def stock_adjustment_create(request):
    if not request.user.can_adjust_stock and not request.user.is_superuser:
        messages.error(request, "You do not have permission to adjust stock.")
        return render(request, 'errors/permission_denied.html', status=403)

    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            store = form.cleaned_data['store']
            product = form.cleaned_data['product']
            quantity = form.cleaned_data['quantity']
            reason = form.cleaned_data['reason']
            adjustment_type = form.cleaned_data['adjustment_type']  # ✅ Use actual form input
            
            # Restrict manager to only their assigned store
            if not request.user.is_superuser and request.user.role == 'manager':
                if store != request.user.store:
                    messages.error(request, "You can only adjust stock for your own store.")
                    return render(request, 'errors/permission_denied.html', status=403)


            stock_entry = Stock.objects.filter(product=product, store=store).first()
            if not stock_entry:
                messages.error(request, "No stock entry for this product in the selected store.")
                return redirect('inventory:stock_adjustment_create')

            store_stock = stock_entry.quantity

            if adjustment_type == 'subtract' and store_stock < quantity:
                messages.error(request, "Insufficient stock in the selected store.")
                return redirect('inventory:stock_adjustment_create')

            # Apply the direction
            adjusted_quantity = abs(quantity) if adjustment_type == 'add' else -abs(quantity)

            try:
                with transaction.atomic():
                    adjustment = StockAdjustment.objects.create(
                        store=store,
                        product=product,
                        quantity=adjusted_quantity,  # ✅ Save the correct signed quantity
                        reason=reason,
                        adjusted_by=request.user  # ✅ Don't forget the user
                    )

                    stock_entry.quantity += adjusted_quantity
                    stock_entry.save()

                    product.total_quantity += adjusted_quantity
                    product.save()

                messages.success(request, "Stock adjustment successfully recorded!")
                AuditLog.objects.create(
                    user=request.user,
                    action='adjustment',
                    description=f"{request.user.username} adjusted {product.name} in {store.name} by {adjusted_quantity} units. Reason: {reason}"
        )
                return redirect('stock_adjustment_list')

            except Exception as e:
                messages.error(request, f"An error occurred: {e}")
                return redirect('inventory:stock_adjustment_create')
    else:
        form = StockAdjustmentForm()
        form.fields['product'].queryset = Product.objects.all()
        form.fields['store'].queryset = Store.objects.all()

    return render(request, 'dashboard/stock_adjustment_form.html', {'form': form})

@login_required
def create_purchase_order(request):
    ItemFormSet = modelformset_factory(PurchaseOrderItem, form=PurchaseOrderItemForm, extra=1, can_delete=True)
    
    if request.method == 'POST':
        po_form = PurchaseOrderForm(request.POST)
        item_formset = ItemFormSet(request.POST, queryset=PurchaseOrderItem.objects.none())

        if po_form.is_valid() and item_formset.is_valid():
            po = po_form.save(commit=False)
            po.created_by = request.user
            po.save()

            for form in item_formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    item = form.save(commit=False)
                    item.purchase_order = po
                    item.save()

            messages.success(request, "Purchase Order created successfully.")
            return redirect('inventory:purchase_order_list')
    else:
        po_form = PurchaseOrderForm()
        item_formset = ItemFormSet(queryset=PurchaseOrderItem.objects.none())

    return render(request, 'dashboard/purchase_order_form.html', {
        'po_form': po_form,
        'item_formset': item_formset,
    })

@login_required
def stock_adjustment_list(request):
    return HttpResponse("Stock Adjustment List Coming Soon")
