# Generated by Django 5.2 on 2025-05-30 17:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0046_customer_store'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customer',
            name='store',
        ),
    ]
