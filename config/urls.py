"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from users.views import (
    CustomLoginView,
    logout_view,
    admin_dashboard,
    manager_dashboard,
    store_dashboard,
    inventory_dashboard,
    sales_dashboard,
    default_dashboard,
)

urlpatterns = [
    path('accounting/', include('accounting.urls', namespace='accounting')),
    path('', RedirectView.as_view(url='/login/', permanent=False)),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('admin/', admin.site.urls),
    path('users/', include('users.urls', namespace='users')),
    path('dashboard/admin/', admin_dashboard, name='admin_dashboard'),
    path('dashboard/manager/', manager_dashboard, name='manager_dashboard'),
    path('dashboard/store/', store_dashboard, name='store_dashboard'),
    path('dashboard/inventory/', inventory_dashboard, name='inventory_dashboard'),
    path('dashboard/sales/', sales_dashboard, name='sales_dashboard'),
    path('dashboard/', default_dashboard, name='default_dashboard'),
    # path('dashboard/', include('inventory.urls')),  # Add this line
    path('accounts/login/', auth_views.LoginView.as_view(), name='account_login'),  # 👈 ADD THIS
    path('dashboard/', include(('inventory.urls', 'inventory'), namespace='inventory')),

]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
