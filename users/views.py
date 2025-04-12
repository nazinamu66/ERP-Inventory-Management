from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView
from .decorators import role_required
from django.contrib.auth import logout



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


@role_required(['admin'])
def admin_dashboard(request):
    return render(request, 'dashboard/admin.html')

@role_required(['manager'])
def manager_dashboard(request):
    return render(request, 'dashboard/manager.html')

@role_required(['staff'])
def store_dashboard(request):
    return render(request, 'dashboard/store.html')

@role_required(['clerk'])
def inventory_dashboard(request):
    return render(request, 'dashboard/inventory.html')

@role_required(['sales'])
def sales_dashboard(request):
    return render(request, 'dashboard/sales.html')

@role_required(['admin', 'manager', 'staff', 'clerk', 'sales'])
def default_dashboard(request):
    return render(request, 'dashboard/default.html')

def logout_view(request):
    logout(request)
    return redirect('login')  # Or wherever you want to send them after logout
