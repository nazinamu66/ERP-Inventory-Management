from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.views import LoginView
from .decorators import role_required
from django.contrib.auth import logout
from inventory.models import Stock
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from inventory.models import Store
from .models import User
from .forms import UserForm
from inventory.models import AuditLog  # add at top if not already
from django.contrib.auth.decorators import login_required, user_passes_test

def is_admin_or_manager(user):
    return user.is_authenticated and (user.role == 'admin' or user.role == 'manager')

@login_required
@user_passes_test(is_admin_or_manager)
def user_create(request):
    if not request.user.is_superuser and request.user.role != 'manager':
        return render(request, 'errors/permission_denied.html', status=403)

    if request.method == 'POST':
        form = UserForm(request.POST, request=request)
        if form.is_valid():
            user = form.save(commit=False)
            if request.user.role == 'manager':
                user.store = request.user.store
            user.set_password('changeme')  # default password
            user.save()
            AuditLog.objects.create(
                user=request.user,
                action='create_user',
                description=f"{request.user.username} created user {user.username} ({user.role}) for store {user.store.name if user.store else 'N/A'}"
            )
            return redirect('users:user_list')
    else:
        form = UserForm(request=request)

    return render(request, 'users/user_form.html', {'form': form})


@login_required
def user_list(request):
    if not request.user.is_superuser and request.user.role != 'manager':
        return render(request, 'errors/permission_denied.html', status=403)

    if request.user.role == 'manager':
        users = User.objects.filter(store=request.user.store)
    else:
        users = User.objects.all()

    return render(request, 'users/user_list.html', {'users': users})



@login_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)

    if not request.user.is_superuser and (request.user.role != 'manager' or user.store != request.user.store):
        return render(request, 'errors/permission_denied.html', status=403)

    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('users:user_list')
    else:
        form = UserForm(instance=user)

    return render(request, 'users/user_form.html', {'form': form})


@login_required
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)

    if not request.user.is_superuser and (request.user.role != 'manager' or user.store != request.user.store):
        return render(request, 'errors/permission_denied.html', status=403)

    if request.method == 'POST':
        AuditLog.objects.create(
            user=request.user,
            action='delete_user',
            description=f"{request.user.username} deleted user {user.username} ({user.role}) from store {user.store.name if user.store else 'N/A'}"
        )
        user.delete()
        return redirect('users:user_list')

    return render(request, 'users/user_confirm_delete.html', {'user': user})



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

@role_required(allowed_roles=['staff'])
def store_dashboard(request):
    store = request.user.store
    stock_items = Stock.objects.filter(store=store).select_related('product')

    context = {
        'stock_items': stock_items,
        'store': store
    }
    return render(request, 'dashboard/store.html', context)

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
