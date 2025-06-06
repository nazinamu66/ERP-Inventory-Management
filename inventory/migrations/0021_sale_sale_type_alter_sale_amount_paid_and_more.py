# Generated by Django 5.2 on 2025-04-29 16:38

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0020_alter_sale_receipt_number_salereturn_salereturnitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='sale_type',
            field=models.CharField(choices=[('receipt', 'Sales Receipt'), ('invoice', 'Invoice')], default='receipt', max_length=10),
        ),
        migrations.AlterField(
            model_name='sale',
            name='amount_paid',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name='sale',
            name='customer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='inventory.customer'),
        ),
        migrations.AlterField(
            model_name='sale',
            name='payment_method',
            field=models.CharField(blank=True, choices=[('cash', 'Cash'), ('bank', 'Bank Transfer'), ('pos', 'POS')], max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='sale',
            name='payment_status',
            field=models.CharField(choices=[('paid', 'Paid'), ('unpaid', 'Unpaid'), ('partial', 'Partially Paid')], default='unpaid', max_length=20),
        ),
        migrations.AlterField(
            model_name='sale',
            name='receipt_number',
            field=models.CharField(blank=True, max_length=50, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='sale',
            name='total_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name='salereturnitem',
            name='sale_item',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='return_items', to='inventory.saleitem'),
        ),
    ]
