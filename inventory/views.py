from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.http import HttpResponse
from inventory.models import StockTransfer, Stock
from inventory.forms import StockTransferForm
from .forms import StockAdjustmentForm, ProductForm
from .models import Product, Store, StockAdjustment


@login_required
def admin_dashboard(request):
    return render(request, 'dashboard/admin.html')


@login_required
def manager_dashboard(request):
    return render(request, 'dashboard/manager.html')


@login_required
def store_dashboard(request):
    return render(request, 'dashboard/staff.html')


@login_required
def inventory_dashboard(request):
    return render(request, 'dashboard/clerk.html')


@login_required
def sales_dashboard(request):
    return render(request, 'dashboard/sales.html')


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
        form = StockTransferForm(request.POST)
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

                messages.success(request, 'Stock transferred successfully!')
                return redirect('inventory:stock_transfer')
            except Exception as e:
                messages.error(request, f"Error during transfer: {e}")

    else:
        form = StockTransferForm()

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
def stock_adjustment_list(request):
    return HttpResponse("Stock Adjustment List Coming Soon")
