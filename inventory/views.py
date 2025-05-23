from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.http import HttpResponse
from inventory.models import StockTransfer,Supplier
from inventory.forms import StockTransferForm
from .forms import StockAdjustmentForm, ProductForm
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


@login_required
def customer_create(request):
    next_url = request.GET.get('next', request.path)  # default to self

    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer added successfully.")
            return HttpResponseRedirect(next_url)
    else:
        form = CustomerForm()

    return render(request, 'dashboard/customer_form.html', {
        'form': form,
        'next': next_url,  # pass this to template for the form action
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

                # ✅ Save the store to the Purchase Order!
                po.status = 'received'
                po.store = store
                po.save()

                # ✅ Audit & accounting
                AuditLog.objects.create(
                    user=request.user,
                    action='adjustment',
                    description=f"{request.user.username} received PO-{po.id} and updated stock at {store.name}.",
                    store=store
                )

                from accounting.services import record_transaction_by_slug
                record_transaction_by_slug(
                    source_slug="accounts-payable",
                    destination_slug="inventory-assets",
                    amount=total_value,
                    description=f"PO-{po.id} Goods Received",
                    supplier=po.supplier,
                    store=store
                )

                messages.success(request, "Purchase Order received and accounting recorded.")
                return redirect('inventory:purchase_order_detail', po_id=po.id)

        except Exception as e:
            logger.error(f"❌ PO receiving failed: {e}")
            messages.error(request, f"An error occurred: {e}")

    stores = Store.objects.all() if request.user.is_superuser or request.user.role == 'admin' else None
    return render(request, 'dashboard/receive_purchase_order.html', {'po': po, 'stores': stores})

@require_POST
@login_required
def purchase_received_delete_view(request, po_id):
    po = get_object_or_404(PurchaseOrder, pk=po_id)

    if not request.user.is_superuser and request.user.role != 'manager':
        return HttpResponseForbidden("Only managers or admins can delete received purchases.")

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
    logs = AuditLog.objects.all().select_related("user")
    users = User.objects.all()
    all_actions = AuditLog.objects.order_by('action').values_list('action', flat=True).distinct()

    user = request.user

    # 🔒 Filter logs by store if manager
    if user.role == "manager" and user.store:
        logs = logs.filter(description__icontains=user.store.name)

    # Apply user filters (admins can override and view all)
    user_id = request.GET.get("user")
    if user_id:
        logs = logs.filter(user_id=user_id)

    action = request.GET.get("action")
    if action:
        logs = logs.filter(action=action)

    start = request.GET.get("start")
    end = request.GET.get("end")
    if start and end:
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
            logs = logs.filter(timestamp__date__range=[start_date, end_date])
        except ValueError:
            pass

    # 🔁 Handle export to PDF
    if request.GET.get("export") == "pdf":
        html_string = render_to_string("pdf/audit_log_pdf.html", {
            "logs": logs.order_by("-timestamp"),
            "request": request,
        })
        pdf = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=audit_logs.pdf"
        return response

    # 🗂️ Paginate results
    paginator = Paginator(logs.order_by("-timestamp"), 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "dashboard/audit_log_list.html", {
        "page_obj": page_obj,
        "users": users,
        "action_choices": all_actions,
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
    total_profit = sum(item.profit for item in sale.items.all())


    return render(request, 'dashboard/sale_detail.html', {
        'sale': sale,
        'items': items,
        'total_profit': total_profit,

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
                sale.save()

                if not sale.receipt_number:
                    sale.receipt_number = f"RCPT-{sale.id:06d}"
                    sale.save(update_fields=["receipt_number"])

                total, cost_total = 0, 0
                store = sale.store

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
                    description=f"{request.user.username} recorded a sale receipt for {sale.customer.name}"
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

                    product = form_item.cleaned_data["product"]
                    quantity = form_item.cleaned_data["quantity"]
                    unit_price = form_item.cleaned_data["unit_price"]

                    stock_entry = Stock.objects.filter(product=product, store=store).first()
                    if not stock_entry or stock_entry.quantity < quantity:
                        messages.error(request, f"Not enough stock for {product.name}")
                        raise ValueError("Stock error")

                    stock_entry.quantity -= quantity
                    stock_entry.save(update_fields=["quantity"])

                    item = form_item.save(commit=False)
                    item.sale = sale
                    item.cost_price = stock_entry.cost_price or 0
                    item.save()

                    total += quantity * unit_price
                    cost_total += quantity * item.cost_price

                sale.total_amount = total
                sale.save(update_fields=["total_amount"])

                revenue_txn = record_transaction_by_slug(
                    source_slug='sales-revenue',
                    destination_slug='accounts-receivable',
                    amount=total,
                    store=store,
                    description=f"Invoice - {sale.receipt_number}"
                )

                cogs_txn = record_transaction_by_slug(
                    source_slug='inventory-assets',
                    destination_slug='cost-of-goods-sold',
                    amount=cost_total,
                    store=store,
                    description=f"COGS for {sale.receipt_number}"
                )

                sale.revenue_transaction = revenue_txn
                sale.cogs_transaction = cogs_txn
                sale.transaction = revenue_txn
                sale.save(update_fields=["revenue_transaction", "cogs_transaction", "transaction"])

                AuditLog.objects.create(
                    user=user,
                    action='adjustment',
                    description=f"{user.username} created invoice {sale.receipt_number} for {sale.customer.name}"
                )

                messages.success(request, f"✅ Invoice No {sale.receipt_number} recorded.")
                return redirect('inventory:invoice_create')

        except Exception as e:
            logger.error(f"Invoice creation failed: {e}")
            messages.error(request, "Something went wrong while saving the invoice.")

    return render(request, 'dashboard/invoice_form.html', {
        'form': form,
        'formset': formset,
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


from django.db.models import Q
from inventory.models import Product, Store
from collections import defaultdict


from collections import defaultdict

@login_required
def stock_list(request):
    user = request.user
    stocks = Stock.objects.select_related('store', 'product')
    stores = Store.objects.all()
    products = Product.objects.all()

    # Restrict stocks by role
    if user.role in ["manager", "clerk", "sales"] and user.store:
        stocks = stocks.filter(store=user.store)
        stores = stores.filter(id=user.store.id)
    else:
        store_id = request.GET.get("store")
        if store_id:
            stocks = stocks.filter(store_id=store_id)

    # Filter by product
    product_id = request.GET.get("product")
    if product_id:
        stocks = stocks.filter(product_id=product_id)

    # ✅ Build totals using product ID (as integer)
    total_per_product = defaultdict(int)
    for stock in stocks:
        total_per_product[int(stock.product.id)] += stock.quantity

    # ✅ Sum for footer (optional)
    overall_total_stock = sum(total_per_product.values())

    return render(request, 'dashboard/stock_list.html', {
        'stocks': stocks,
        'stores': stores,
        'products': products,
        'selected_store': request.GET.get("store", ""),
        'selected_product': request.GET.get("product", ""),
        'total_per_product': total_per_product,
        'overall_total_stock': overall_total_stock,
    })

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
            transfer = form.save(commit=False)
            transfer.status = 'requested'  # Always start as request
            transfer.save()

            messages.success(request, 'Stock transfer request submitted and awaiting approval.')
            return redirect('inventory:stock_transfer_list')
    else:
        form = StockTransferForm(request=request)

    return render(request, 'dashboard/stock_transfer.html', {'form': form})

# from django.views.decorators.http import require_POST

@require_POST
@login_required
def approve_transfer(request, transfer_id):
    if not request.user.is_superuser and request.user.role != 'admin':
        return HttpResponseForbidden("Only admins can approve transfers.")

    transfer = get_object_or_404(StockTransfer, id=transfer_id)

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

            # Reduce source
            source_stock.quantity -= transfer.quantity
            source_stock.save()

            # Increase destination
            dest_stock, created = Stock.objects.get_or_create(
                product=transfer.product,
                store=transfer.destination_store,
                defaults={'quantity': 0}
            )
            dest_stock.quantity += transfer.quantity
            dest_stock.save()

            transfer.status = 'approved'
            transfer.save()

            AuditLog.objects.create(
                user=request.user,
                action='transfer_approval',
                description=f"{request.user.username} approved stock transfer #{transfer.id}"
            )

            messages.success(request, "Transfer approved successfully.")
    except Exception as e:
        messages.error(request, f"Error approving transfer: {e}")

    return redirect('inventory:stock_transfer_list')


@require_POST
@login_required
def reject_transfer(request, transfer_id):
    if not request.user.is_superuser and request.user.role != 'admin':
        return HttpResponseForbidden("Only admins can reject transfers.")

    transfer = get_object_or_404(StockTransfer, id=transfer_id)

    if transfer.status != 'requested':
        messages.warning(request, "This transfer has already been processed.")
    else:
        transfer.status = 'rejected'
        transfer.save()

        AuditLog.objects.create(
            user=request.user,
            action='transfer_rejection',
            description=f"{request.user.username} rejected stock transfer #{transfer.id}"
        )
        messages.success(request, "Transfer rejected.")

    return redirect('inventory:stock_transfer_list')


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
            supplier, _ = Supplier.objects.get_or_create(name__iexact=supplier_name.strip(), defaults={"name": supplier_name})
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

    return render(request, 'dashboard/purchase_order_form.html', {
        'item_formset': item_formset,
        'suppliers': Supplier.objects.all(),
    })


@require_POST
@login_required
def purchase_order_delete_view(request, pk):
    if not request.user.is_superuser and request.user.role != 'manager':
        return HttpResponseForbidden("Only managers or admins can delete purchase orders.")

    po = get_object_or_404(PurchaseOrder, pk=pk)

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
