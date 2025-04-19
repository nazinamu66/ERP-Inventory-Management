from django.urls import path
from .views import CustomLoginView
from . import views

app_name = 'users'

urlpatterns = [
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('login/', CustomLoginView.as_view(), name='login'),
    
]
