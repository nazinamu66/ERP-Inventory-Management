# Generated by Django 5.2 on 2025-04-18 14:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0010_remove_purchase_item_remove_sale_item_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockadjustment',
            name='adjustment_type',
            field=models.CharField(choices=[('add', 'Add'), ('subtract', 'Subtract')], default='add', max_length=10),
        ),
        migrations.AlterField(
            model_name='stockadjustment',
            name='quantity',
            field=models.IntegerField(help_text='Enter a positive number only.'),
        ),
    ]
