from django.urls import path
from inventory.views import audit_log_list_view
from . import views
from .models import Purchase
from .views import purchase_create  # import the view
from .views import product_create  # import the view
from .views import get_stock_quantity
from .views import sale_create  # import the view
from .views import sale_list_view  # import the view
from .views import export_sales_csv  # import the view
from .views import export_sales_pdf  # import the view
from .views import create_purchase_order  # import the view
from .views import purchase_order_list  # import the view
from .views import add_supplier  # import the view
from .views import receive_purchase_order, purchase_order_detail
from django.conf import settings
from django.conf.urls.static import static
from .views import export_po_pdf




from .views import (
    product_list,
    stock_list,
    stock_transfer_view,
    stock_transfer_list_view,  # ✅ NEW VIEW
    product_edit,
    redirect_dashboard,
    sales_dashboard,
    manager_dashboard,
    store_dashboard,
    inventory_report_view,
    export_inventory_csv,
    export_inventory_pdf,
    export_purchase_orders_pdf,
    export_purchase_orders_csv,
    export_po_receipt_pdf,
    supplier_edit,
    supplier_list,
    customer_create,

)

app_name = 'inventory'

urlpatterns = [
    path('products/', product_list, name='product_list'),
    path('stocks/', stock_list, name='stock_list'),
    path('stock-transfer/', stock_transfer_view, name='stock_transfer'),
    path('stock-transfers/', stock_transfer_list_view, name='stock_transfer_list'),  # ✅ NEW ROUTE
    path('products/add/', product_create, name='product_create'),  # ✅ add this
    path('products/<int:pk>/edit/', product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('stock-adjustment/', views.stock_adjustment_create, name='stock_adjustment_create'),
    path('stock-adjustments/', views.stock_adjustment_list, name='stock_adjustment_list'),
    path('audit-logs/', audit_log_list_view, name='audit_log_list'),
    path('purchases/add/', purchase_create, name='purchase_create'),
    path('sales/add/', sale_create, name='sale_create'),
    path('api/get-stock/', get_stock_quantity, name='get_stock_quantity'),
    path('sales/history/', sale_list_view, name='sale_list'),
    path('sales/export/', export_sales_csv, name='export_sales_csv'),
    path('sales/export/pdf/', export_sales_pdf, name='export_sales_pdf'),
    path('purchases/new/', create_purchase_order, name='create_purchase_order'),
    path('suppliers/add/', add_supplier, name='add_supplier'),
    path('purchases/', purchase_order_list, name='purchase_order_list'),
    path('purchases/receive/<int:po_id>/', receive_purchase_order, name='receive_purchase_order'),
    path('purchases/<int:po_id>/', purchase_order_detail, name='purchase_order_detail'),
    path('purchases/export/pdf/<int:po_id>/', export_po_pdf, name='export_po_pdf'),
    path('dashboard/', redirect_dashboard, name='dashboard'),
    path('dashboard/sales/', sales_dashboard, name='sales_dashboard'),
    path('dashboard/manager/', manager_dashboard, name='manager_dashboard'),
    path('dashboard/store/', store_dashboard, name='store_dashboard'),
    path('dashboard/inventory/report/', inventory_report_view, name='inventory_report'),
    path('dashboard/inventory/export/csv/', export_inventory_csv, name='export_inventory_csv'),
    path('dashboard/inventory/export/pdf/', export_inventory_pdf, name='export_inventory_pdf'),
    path('dashboard/purchases/export/csv/', export_purchase_orders_csv, name='export_purchase_orders_csv'),
    path('dashboard/purchases/export/pdf/', export_purchase_orders_pdf, name='export_purchase_orders_pdf'),
    path('purchases/<int:po_id>/receipt/pdf/', export_po_receipt_pdf, name='export_po_receipt_pdf'),
    path('suppliers/', supplier_list, name='supplier_list'),
    path('suppliers/<int:supplier_id>/edit/', supplier_edit, name='supplier_edit'),
    path('customers/new/', customer_create, name='customer_create'),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
