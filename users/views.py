from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.views import LoginView
from .decorators import role_required
from django.contrib.auth import logout
from django.shortcuts import render, redirect, get_object_or_404
from inventory.models import PurchaseOrder
from .models import User
from .forms import UserForm
from inventory.models import AuditLog  # add at top if not already
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.timezone import now
from django.db.models.functions import TruncDate
from datetime import timedelta
import json
from inventory.models import Product, Stock
from inventory.models import Sale, SaleItem
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from accounting.models import ExpenseEntry





def is_admin_or_manager(user):
    return user.is_authenticated and (user.role == 'admin' or user.role == 'manager')

@login_required
@user_passes_test(is_admin_or_manager)
def user_create(request):
    if not request.user.is_superuser and request.user.role != 'manager':
        return render(request, 'errors/permission_denied.html', status=403)

    if request.method == 'POST':
        form = UserForm(request.POST, request=request)
        if form.is_valid():
            user = form.save()  # Handles password and stores

            # For managers, enforce store if none was selected
            if request.user.role == 'manager' and not user.stores.exists():
                user.stores.set([request.user.store])

            store_names = ", ".join(s.name for s in user.stores.all()) or "N/A"
            AuditLog.objects.create(
                user=request.user,
                action='create_user',
                description=f"{request.user.username} created user {user.username} ({user.role}) for store(s): {store_names}"
            )
            return redirect('users:user_list')
    else:
        form = UserForm(request=request)

    return render(request, 'users/user_form.html', {'form': form})


@login_required
def user_list(request):
    if not request.user.is_superuser and request.user.role != 'manager':
        return render(request, 'errors/permission_denied.html', status=403)

    if request.user.role == 'manager':
        # Managers can only see users in their own stores
        users = User.objects.filter(stores__in=request.user.stores.all()).distinct()
    else:
        users = User.objects.all()

    return render(request, 'users/user_list.html', {'users': users})



@login_required
def user_edit(request, pk):
    user_to_edit = get_object_or_404(User, pk=pk)

    if not request.user.is_superuser:
        if request.user.role != 'manager':
            return render(request, 'errors/permission_denied.html', status=403)

        # Managers can only edit users assigned to their stores
        if not user_to_edit.stores.filter(id__in=request.user.stores.values_list('id', flat=True)).exists():
            return render(request, 'errors/permission_denied.html', status=403)

    if request.method == 'POST':
        form = UserForm(request.POST, instance=user_to_edit, request=request)
        if form.is_valid():
            form.save()
            return redirect('users:user_list')
    else:
        form = UserForm(instance=user_to_edit, request=request)

    return render(request, 'users/user_form.html', {'form': form})



@login_required
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)

    if not request.user.is_superuser and (request.user.role != 'manager' or user.store != request.user.store):
        return render(request, 'errors/permission_denied.html', status=403)

    if request.method == 'POST':
        AuditLog.objects.create(
            user=request.user,
            action='delete_user',
            description=f"{request.user.username} deleted user {user.username} ({user.role}) from store {user.store.name if user.store else 'N/A'}"
        )
        user.delete()
        return redirect('users:user_list')

    return render(request, 'users/user_confirm_delete.html', {'user': user})



class CustomLoginView(LoginView):
    template_name = 'users/login.html'

    def get_success_url(self):
        user = self.request.user
        role = getattr(user, 'role', 'staff')  # Fallback to 'staff'

        if role == 'admin':
            return reverse_lazy('admin_dashboard')
        elif role == 'manager':
            return reverse_lazy('manager_dashboard')
        elif role == 'staff':
            return reverse_lazy('store_dashboard')
        elif role == 'clerk':
            return reverse_lazy('inventory_dashboard')
        elif role == 'sales':
            return reverse_lazy('sales_dashboard')

        return reverse_lazy('default_dashboard')




def get_sales_over_time():
    today = now().date()
    start_of_week = today - timedelta(days=6)

    sales = (
        Sale.objects
        .filter(sale_date__date__range=(start_of_week, today))
        .annotate(day=TruncDate('sale_date'))
        .values('day')
        .annotate(total=Sum('total_amount'))
        .order_by('day')
    )

    day_totals = {entry['day']: float(entry['total']) for entry in sales}
    labels = [(start_of_week + timedelta(days=i)).strftime('%a') for i in range(7)]
    values = [day_totals.get(start_of_week + timedelta(days=i), 0) for i in range(7)]

    return json.dumps(labels), json.dumps(values)


def get_top_selling_products(limit=5):
    top_products = (
        SaleItem.objects
        .values('product__name')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:limit]
    )

    labels = [p['product__name'] for p in top_products]
    values = [p['total_qty'] for p in top_products]

    return json.dumps(labels), json.dumps(values)


def get_sales_by_store():
    store_sales = (
        Sale.objects
        .values('store__name')
        .annotate(total=Sum('total_amount'))
        .order_by('-total')
    )

    labels = [entry['store__name'] for entry in store_sales]
    values = [float(entry['total']) for entry in store_sales]

    return json.dumps(labels), json.dumps(values)


@login_required
def admin_dashboard(request):
    today = now().date()
    start_of_week = today - timedelta(days=6)

    # Revenue over past 7 days
    today = now().date()
    start_of_week = today - timedelta(days=6)

    revenue_by_day = (
        Sale.objects
        .filter(sale_date__date__range=(start_of_week, today))
        .annotate(day=TruncDate('sale_date'))
        .values('day')
        .annotate(total=Sum('total_amount'))
        .order_by('day')
    )

    sales = (
        SaleItem.objects
        .filter(sale__sale_date__date__range=(start_of_week, today))
        .annotate(day=TruncDate('sale__sale_date'))
        .annotate(profit=ExpressionWrapper(
            (F('unit_price') - F('cost_price')) * F('quantity'),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        ))
        .values('day')
        .annotate(total_profit=Sum('profit'))
        .order_by('day')
    )

    profit_map = {entry['day']: float(entry['total_profit']) for entry in sales}
    profit_labels = [(start_of_week + timedelta(days=i)).strftime('%a') for i in range(7)]
    profit_values = [profit_map.get(start_of_week + timedelta(days=i), 0) for i in range(7)]


    day_map = {entry['day']: float(entry['total']) for entry in revenue_by_day}
    revenue_labels = [(start_of_week + timedelta(days=i)).strftime('%a') for i in range(7)]
    revenue_values = [day_map.get(start_of_week + timedelta(days=i), 0) for i in range(7)]

    # 💰 Total Revenue
    revenue = Sale.objects.aggregate(total=Sum('total_amount'))['total'] or 0

    # 💸 Cost of Goods Sold (COGS)
    cogs_qs = SaleItem.objects.annotate(
        cost=ExpressionWrapper(F('cost_price') * F('quantity'), output_field=DecimalField())
    )
    cogs = cogs_qs.aggregate(total=Sum('cost'))['total'] or 0

    # 🧾 Expenses
    expenses = ExpenseEntry.objects.aggregate(total=Sum('amount'))['total'] or 0

    # 🧮 Net Profit
    net_profit = revenue - cogs - expenses

  

    # Metrics
    total_products = Product.objects.count()
    total_stock = Stock.objects.aggregate(total=Sum('quantity'))['total'] or 0
    sales_today = Sale.objects.filter(sale_date__date=today).count()
    sales_this_week = Sale.objects.filter(sale_date__date__gte=start_of_week).count()
    total_sales = Sale.objects.count()
    total_revenue = Sale.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    low_stock_products = (
        Product.objects
        .annotate(total_store_quantity=Sum('stock__quantity'))
        .filter(total_store_quantity__lt=10)
    )

    recent_sales = (
        SaleItem.objects
        .select_related('sale', 'product', 'sale__store')
        .order_by('-sale__sale_date')[:5]
    )

    # Charts
    chart_labels, chart_values = get_sales_over_time()
    product_labels, product_values = get_top_selling_products()
    store_labels, store_values = get_sales_by_store()

    context = {
        'total_revenue': revenue,
        'net_profit': net_profit,
        'total_products': total_products,
        'total_stock': total_stock,
        'sales_today': sales_today,
        'sales_this_week': sales_this_week,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'low_stock_products': low_stock_products,
         'revenue_labels': json.dumps(revenue_labels),
        'revenue_values': json.dumps(revenue_values),
        'recent_sales': recent_sales,

        # chart data
        'chart_labels': chart_labels,
        'chart_values': chart_values,
        'product_labels': product_labels,
        'product_values': product_values,
        'store_labels': store_labels,
        'store_values': store_values,
        'profit_labels': profit_labels,
        'profit_values': profit_values,
    }

    return render(request, 'dashboard/admin.html', context)

# users/models.py
def get_active_store(self, request):
    store_id = request.GET.get("store")
    if store_id:
        return self.stores.filter(id=store_id).first()
    return self.stores.first()


from django.db.models import Q

@role_required(['manager'])
@login_required
def manager_dashboard(request):
    user = request.user
    stores = user.stores.all()

    if not stores.exists():
        messages.warning(request, "No store assigned to your account.")
        return render(request, 'dashboard/default.html')

    today = now().date()
    start_of_week = today - timedelta(days=6)

    selected_store_id = request.GET.get("store")  # store ID or 'all'
    show_all = selected_store_id == "all"

    if show_all or stores.count() == 1:
        selected_store = None if show_all else stores.first()
        store_filter = Q(store__in=stores)
    else:
        selected_store = stores.filter(id=selected_store_id).first()
        store_filter = Q(store=selected_store) if selected_store else Q(store__in=stores)

    # Get data based on store filter
    store_sales = Sale.objects.filter(store_filter)
    store_stock = Stock.objects.filter(store_filter).select_related('product')

    # KPIs
    total_products = store_stock.values('product').distinct().count()
    total_stock = store_stock.aggregate(qty=Sum('quantity'))['qty'] or 0
    sales_today = store_sales.filter(sale_date__date=today).count()
    sales_week = store_sales.filter(sale_date__date__gte=start_of_week).count()
    total_revenue = store_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    top_products = (
        SaleItem.objects
        .filter(sale__in=store_sales)
        .values('product__name')
        .annotate(qty=Sum('quantity'))
        .order_by('-qty')[:5]
    )
    product_labels = [p['product__name'] for p in top_products]
    product_values = [p['qty'] for p in top_products]

    revenue_by_day = (
        store_sales
        .annotate(day=TruncDate('sale_date'))
        .values('day')
        .annotate(total=Sum('total_amount'))
        .order_by('day')
    )
    day_map = {entry['day']: float(entry['total']) for entry in revenue_by_day}
    revenue_labels = [(start_of_week + timedelta(days=i)).strftime('%a') for i in range(7)]
    revenue_values = [day_map.get(start_of_week + timedelta(days=i), 0) for i in range(7)]

    return render(request, 'dashboard/manager.html', {
        'stores': stores,
        'selected_store': selected_store,
        'show_all': show_all,
        'total_products': total_products,
        'total_stock': total_stock,
        'sales_today': sales_today,
        'sales_week': sales_week,
        'total_revenue': total_revenue,
        'product_labels': json.dumps(product_labels),
        'product_values': json.dumps(product_values),
        'revenue_labels': json.dumps(revenue_labels),
        'revenue_values': json.dumps(revenue_values),
        'recent_purchase_orders': PurchaseOrder.objects.filter(created_by=user).order_by('-date')[:5],
    })

from django.contrib import messages
from django.shortcuts import render
from inventory.models import Stock, Sale

@role_required(allowed_roles=['staff'])
def store_dashboard(request):
    store = getattr(request.user, 'store', None)

    if not store:
        messages.warning(request, "You are not assigned to a store.")
        return render(request, 'dashboard/default.html')

    stock_items = Stock.objects.filter(store=store).select_related('product')
    recent_sales = Sale.objects.filter(store=store).order_by('-sale_date')[:10]

    context = {
        'store': store,
        'stock_items': stock_items,
        'recent_sales': recent_sales,
    }
    return render(request, 'dashboard/store.html', context)

@role_required(['clerk'])
def inventory_dashboard(request):
    store = getattr(request.user, 'store', None)

    if not store:
        messages.warning(request, "No store assigned to your account.")
        return render(request, 'dashboard/default.html')

    stock_items = Stock.objects.filter(store=store).select_related('product')

    total_products = stock_items.count()
    total_quantity = stock_items.aggregate(total=Sum('quantity'))['total'] or 0

    # Optional: track low stock items
    low_stock_items = stock_items.filter(quantity__lt=10)

    context = {
        'store': store,
        'stocks': stock_items,
        'total_products': total_products,
        'total_quantity': total_quantity,
        'low_stock_items': low_stock_items,
    }

    return render(request, 'dashboard/inventory.html', context)

@role_required(['sales'])
def sales_dashboard(request):
    from datetime import timedelta
    from django.utils.timezone import now
    from inventory.models import Sale, SaleItem
    from django.db.models import Sum, F
    from collections import defaultdict

    user = request.user
    today = now().date()

    # ✅ Sales today
    today_sales = (
        Sale.objects
        .filter(sale_date__date=today, sold_by=user)
        .prefetch_related('items__product')
    )

    total_sales_count = today_sales.count()
    total_sales_value = today_sales.aggregate(total=Sum('total_amount'))['total'] or 0
    total_items_sold = SaleItem.objects.filter(sale__in=today_sales).aggregate(qty=Sum('quantity'))['qty'] or 0

    recent_items = (
        SaleItem.objects
        .filter(sale__in=today_sales)
        .select_related('product', 'sale__store')
        .order_by('-sale__sale_date')[:10]
    )

    # 📈 Sales trend (past 7 days)
    sales_trend_data = []
    sales_trend_labels = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        label = day.strftime('%a')  # Mon, Tue...
        count = SaleItem.objects.filter(sale__sale_date__date=day, sale__sold_by=user).aggregate(qty=Sum('quantity'))['qty'] or 0
        sales_trend_labels.append(label)
        sales_trend_data.append(count)

    # 🏆 Top 5 products sold by this user (past 7 days)
    recent_sales = SaleItem.objects.filter(
        sale__sold_by=user,
        sale__sale_date__date__gte=today - timedelta(days=7)
    ).values('product__name').annotate(
        total_qty=Sum('quantity')
    ).order_by('-total_qty')[:5]

    top_products_labels = [item['product__name'] for item in recent_sales]
    top_products_data = [item['total_qty'] for item in recent_sales]

    return render(request, 'dashboard/sales.html', {
        'today_sales': today_sales,
        'total_sales_count': total_sales_count,
        'total_sales_value': total_sales_value,
        'total_items_sold': total_items_sold,
        'recent_items': recent_items,
        'today': today,
        'sales_trend_labels': sales_trend_labels,
        'sales_trend_data': sales_trend_data,
        'top_products_labels': top_products_labels,
        'top_products_data': top_products_data,
    })

@role_required(['admin', 'manager', 'staff', 'clerk', 'sales'])
def default_dashboard(request):
    return render(request, 'dashboard/default.html')

def logout_view(request):
    logout(request)
    return redirect('login')  # Or wherever you want to send them after logout
