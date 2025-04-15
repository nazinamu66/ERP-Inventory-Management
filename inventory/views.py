from django.contrib.auth.decorators import login_required
from .models import Product
from .models import Stock
from django.shortcuts import render, redirect
from django.contrib import messages
from inventory.models import StockTransfer, Stock
from inventory.forms import StockTransferForm
from django.http import Http404

@login_required
def stock_transfer_view(request):
    if request.method == 'POST':
        form = StockTransferForm(request.POST)
        if form.is_valid():
            item = form.cleaned_data['item']
            source_store = form.cleaned_data['source_store']
            destination_store = form.cleaned_data['destination_store']
            quantity = form.cleaned_data['quantity']

            source_stock = Stock.objects.filter(product=item, store=source_store).first()
            destination_stock = Stock.objects.filter(product=item, store=destination_store).first()

            if not source_stock or source_stock.quantity < quantity:
                messages.error(request, 'Insufficient stock in source store or item not found.')
                return render(request, 'dashboard/stock_transfer.html', {'form': form})

            # Decrease stock from source
            source_stock.quantity -= quantity
            source_stock.save()

            # Increase stock in destination
            if destination_stock:
                destination_stock.quantity += quantity
                destination_stock.save()
            else:
                destination_stock = Stock.objects.create(
                    product=item,
                    store=destination_store,
                    quantity=quantity
                )

            # Save the transfer record
            StockTransfer.objects.create(
                item=item,
                source_store=source_store,
                destination_store=destination_store,
                quantity=quantity
            )

            messages.success(request, 'Stock transferred successfully!')
            return redirect('inventory:stock_transfer')
    else:
        form = StockTransferForm()

    return render(request, 'dashboard/stock_transfer.html', {'form': form})

def product_list(request) :
    products = Product.objects.all()
    return render(request, 'dashboard/product_list.html', {'products': products})

def stock_list(request):
    stocks =Stock.objects.select_related('store' , 'product')
    return render(request, 'dashboard/stock_list.html', {'stocks': stocks})

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
