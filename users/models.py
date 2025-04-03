from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Store Manager'),
        ('staff', 'Store Staff'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    store = models.ForeignKey("inventory.Store", on_delete=models.SET_NULL, null=True, blank=True)

    groups = models.ManyToManyField(Group, related_name="custom_user_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="custom_user_permissions", blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"
