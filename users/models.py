from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Store Staff'),
        ('clerk', 'Inventory Clerk'),
        ('sales', 'Sales Staff'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')

    # 💡 Changed from ForeignKey to ManyToManyField
    stores = models.ManyToManyField("inventory.Store", blank=True)

    def get_active_store(self, request):
        """
        Determines the active store for the current request.
        """
        store_id = request.GET.get("store") or request.POST.get("store")
        if store_id and self.stores.filter(id=store_id).exists():
            return self.stores.filter(id=store_id).first()
        return self.stores.first()

    can_view_transfers = models.BooleanField(default=False)
    can_adjust_stock = models.BooleanField(default=False)
    can_transfer_stock = models.BooleanField(default=False)
    can_approve_transfers = models.BooleanField(default=False)


    groups = models.ManyToManyField(Group, related_name="custom_user_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="custom_user_permissions", blank=True)

    @property
    def store(self):
        return self.stores.first()  # or raise if strict


    def __str__(self):
        return f"{self.username} ({self.role})"

from django.db import models
from django.conf import settings

class LoginActivity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} logged in at {self.timestamp}"



