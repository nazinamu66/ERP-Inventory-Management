# Generated by Django 5.2 on 2025-05-29 19:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0042_stocktransfer_transfer_transaction_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='company_profile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stores', to='inventory.companyprofile'),
        ),
    ]
