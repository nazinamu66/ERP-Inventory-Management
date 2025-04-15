from django.urls import path
from .views import product_list, stock_list, stock_transfer_view

app_name = 'inventory'

urlpatterns = [
    path('products/', product_list, name='product_list'),
    path('stocks/', stock_list, name='stock_list'),
    path('stock-transfer/', stock_transfer_view, name='stock_transfer'),
]
