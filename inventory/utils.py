from django.db.models import Max
from datetime import timedelta, date
from inventory.models import SaleItem, Stock

def get_inventory_aging_data(user, store=None, start_date=None, end_date=None, status_filter=None):
    today = date.today()

    # Step 1: Get last sale date per product
    sales_qs = SaleItem.objects.select_related('sale').all()

    if store:
        sales_qs = sales_qs.filter(sale__store=store)
    elif not user.is_superuser:
        allowed_store_ids = user.stores.values_list('id', flat=True)
        sales_qs = sales_qs.filter(sale__store__in=allowed_store_ids)

    last_sales = (
        sales_qs
        .values('product_id')
        .annotate(last_sold=Max('sale__sale_date'))
    )
    last_sale_map = {item['product_id']: item['last_sold'] for item in last_sales}

    # Step 2: Get stock entries
    stock_qs = Stock.objects.select_related('product')

    if store:
        stock_qs = stock_qs.filter(store=store)
    elif not user.is_superuser:
        stock_qs = stock_qs.filter(store__in=user.stores.all())

    # Step 3: Build aging report
    report = []
    for entry in stock_qs:
        product = entry.product
        last_sold = last_sale_map.get(product.id)
        days_since = (today - last_sold.date()).days if last_sold else None

        if days_since is None:
            status = 'No Sales'
        elif days_since <= 30:
            status = 'Fresh'
        elif 30 < days_since <= 90:
            status = 'Stale'
        else:
            status = 'Critical'

        if start_date and last_sold and last_sold.date() < start_date:
            continue
        if end_date and last_sold and last_sold.date() > end_date:
            continue
        if status_filter and status != status_filter:
            continue

        report.append({
            'product': product,
            'quantity': entry.quantity,
            'last_sold': last_sold.date() if last_sold else None,
            'days_since': days_since,
            'status': status
        })

    return report
