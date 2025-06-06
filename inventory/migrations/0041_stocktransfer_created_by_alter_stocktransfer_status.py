# Generated by Django 5.2 on 2025-05-25 19:30

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0040_alter_product_sku'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='stocktransfer',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_transfers', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='stocktransfer',
            name='status',
            field=models.CharField(choices=[('requested', 'Requested'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='requested', max_length=20),
        ),
    ]
