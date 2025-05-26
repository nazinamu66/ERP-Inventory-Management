from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views import (
    stock_transfer_list_view,
    stock_transfer_create,     # ✅ was wrongly named as stock_transfer_view
    approve_transfer,
    reject_transfer,
)



app_name = 'inventory'

urlpatterns = [
    # Dashboard Redirects
    path('dashboard/', views.redirect_dashboard, name='dashboard'),
    # path('dashboard/sales/', views.sales_dashboard, name='sales_dashboard'),
    # path('dashboard/manager/', views.manager_dashboard, name='manager_dashboard'),
    # path('dashboard/store/', views.store_dashboard, name='store_dashboard'),

    # Products & Stock
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('stocks/', views.stock_list, name='stock_list'),
    path('stock-adjustment/', views.stock_adjustment_create, name='stock_adjustment_create'),
    path('stock-adjustments/', views.stock_adjustment_list, name='stock_adjustment_list'),
    path('api/get-stock/', views.get_stock_quantity, name='get_stock_quantity'),
    path('transfers/<int:transfer_id>/slip/', views.transfer_slip_pdf, name='transfer_slip_pdf'),
    path('aging-report/', views.inventory_aging_report, name='inventory_aging_report'),



    # Audit Logs
    path('audit-logs/', views.audit_log_list_view, name='audit_log_list'),
    path('audit-logs/<int:pk>/', views.audit_log_detail_view, name='log_detail'),

    # Purchase Orders
    path('purchases/new/', views.create_purchase_order, name='create_purchase_order'),
    path('purchases/', views.purchase_order_list, name='purchase_order_list'),
    path('purchases/<int:po_id>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('purchases/<int:pk>/delete/', views.purchase_order_delete_view, name='purchase_delete'),
    path('api/get-product-prices/', views.get_product_prices, name='get_product_prices'),
    path('purchases/<int:po_id>/received/delete/', views.purchase_received_delete_view, name='purchase_received_delete'),



    path('purchases/receive/<int:po_id>/', views.receive_purchase_order, name='receive_purchase_order'),

    # Purchase Order Exports
    path('purchases/export/pdf/<int:po_id>/', views.export_po_pdf, name='export_po_pdf'),
    path('purchases/<int:po_id>/receipt/pdf/', views.export_po_receipt_pdf, name='export_po_receipt_pdf'),
    path('dashboard/purchases/export/csv/', views.export_purchase_orders_csv, name='export_purchase_orders_csv'),
    path('dashboard/purchases/export/pdf/', views.export_purchase_orders_pdf, name='export_purchase_orders_pdf'),

    # Sales (Split Forms: Receipt & Invoice)
    path('sales/add-receipt/', views.sale_receipt_create, name='sale_receipt_create'),
    path('sales/add-invoice/', views.invoice_create, name='invoice_create'),


    path('sales/<int:pk>/', views.sale_detail_view, name='sale_detail'),
    path('sales/<int:sale_id>/delete/', views.delete_sale, name='sale_delete'),
    path('sales/<int:sale_id>/return/', views.sale_return_view, name='sale_return'),
    path('sales/history/', views.sale_list_view, name='sale_list'),
    path('sales/export/', views.export_sales_csv, name='export_sales_csv'),
    path('sales/export/pdf/', views.export_sales_pdf, name='export_sales_pdf'),
    path('sales/<int:sale_id>/receipt/pdf/', views.sale_receipt_pdf, name='sale_receipt_pdf'),

    
    # Customers & Suppliers
    path('customers/new/', views.customer_create, name='customer_create'),
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.add_supplier, name='add_supplier'),
    path('suppliers/<int:supplier_id>/edit/', views.supplier_edit, name='supplier_edit'),
    

    # Inventory Report
    path('dashboard/inventory/report/', views.inventory_report_view, name='inventory_report'),
    path('dashboard/inventory/export/csv/', views.export_inventory_csv, name='export_inventory_csv'),
    path('dashboard/inventory/export/pdf/', views.export_inventory_pdf, name='export_inventory_pdf'),


    # inventory/urls.py

    path('transfers/', stock_transfer_list_view, name='stock_transfer_list'),
    path('transfers/new/', views.stock_transfer_create, name='stock_transfer_create'),
    path('transfers/<int:transfer_id>/approve/', approve_transfer, name='approve_transfer'),
    path('transfers/<int:transfer_id>/reject/', reject_transfer, name='reject_transfer'),

    
]

# Static file serving
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
