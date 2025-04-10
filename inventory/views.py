from django.shortcuts import render
from django.contrib.auth.decorators import login_required

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
