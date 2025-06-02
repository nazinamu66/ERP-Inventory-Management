from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils.timezone import now
from inventory.models import AuditLog
from django.contrib.auth import get_user_model

User = get_user_model()


def get_client_ip(request):
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    return x_forwarded.split(",")[0] if x_forwarded else request.META.get("REMOTE_ADDR")


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    AuditLog.objects.create(
        user=user,
        action="login",
        description=f"{user.username} logged in from IP {get_client_ip(request)}",
        timestamp=now()
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    AuditLog.objects.create(
        user=user,
        action="logout",
        description=f"{user.username} logged out from IP {get_client_ip(request)}",
        timestamp=now()
    )
