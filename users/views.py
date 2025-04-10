from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from .models import User

class CustomLoginView(LoginView):
    template_name = 'users/login.html'

    def get_success_url(self):
        user = self.request.user
        
        # Safely get the 'role' attribute and set a default role if it doesn't exist
        role = getattr(user, 'role', 'staff')  # Default to 'staff' if 'role' doesn't exist

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

        # Default fallback to the dashboard if the role isn't matched
        return reverse_lazy('default_dashboard')

# Dashboard views remain the same
@login_required
def admin_dashboard(request):
    return render(request, 'dashboard/admin.html')

@login_required
def manager_dashboard(request):
    return render(request, 'dashboard/manager.html')

@login_required
def store_dashboard(request):
    return render(request, 'dashboard/store.html')

@login_required
def inventory_dashboard(request):
    return render(request, 'dashboard/inventory.html')

@login_required
def sales_dashboard(request):
    return render(request, 'dashboard/sales.html')

@login_required
def default_dashboard(request):
    return render(request, 'dashboard/default.html')
