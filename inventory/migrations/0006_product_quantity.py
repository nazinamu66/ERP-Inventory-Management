# Generated by Django 5.2 on 2025-04-17 14:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_remove_stocktransfer_transfer_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='quantity',
            field=models.PositiveBigIntegerField(default=0),
        ),
    ]
