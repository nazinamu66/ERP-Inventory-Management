from django.shortcuts import redirect, render
from functools import wraps

def role_required(allowed_roles=[]):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            elif request.user.role not in allowed_roles:
                return render(request, 'errors/permission_denied.html')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
