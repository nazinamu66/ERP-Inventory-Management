# Generated by Django 5.2 on 2025-05-06 15:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0016_alter_account_slug'),
        ('inventory', '0028_remove_purchase_supplier_name_purchase_supplier'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='store',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='inventory.store'),
        ),
    ]
