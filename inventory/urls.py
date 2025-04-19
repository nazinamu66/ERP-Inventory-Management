from django.urls import path
from . import views
from .views import product_create  # import the view
from .views import (
    product_list,
    stock_list,
    stock_transfer_view,
    stock_transfer_list_view,  # ✅ NEW VIEW
    product_edit,
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
    

]
