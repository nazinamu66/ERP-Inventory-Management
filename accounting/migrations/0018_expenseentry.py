# Generated by Django 5.2 on 2025-05-15 16:11

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0017_transaction_store'),
        ('inventory', '0032_stocktransfer_status'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ExpenseEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('description', models.TextField(blank=True)),
                ('date', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expense_account', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='expenses', to='accounting.account')),
                ('payment_account', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payments', to='accounting.account')),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='inventory.store')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
