from django.db import migrations

def create_default_accounts(apps, schema_editor):
    Account = apps.get_model('accounting', 'Account')

    default_accounts = [
        {'name': 'Cash', 'type': 'asset'},
        {'name': 'Bank', 'type': 'asset'},
        {'name': 'Accounts Receivable', 'type': 'asset'},
        {'name': 'Accounts Payable', 'type': 'liability'},
        {'name': 'Sales Revenue', 'type': 'revenue'},
        {'name': 'Purchases', 'type': 'expense'},
    ]

    for acc in default_accounts:
        Account.objects.get_or_create(name=acc['name'], type=acc['type'])

class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0002_remove_account_description_remove_account_is_active_and_more'),  # 👈 make sure the last migration number matches
    ]

    operations = [
        migrations.RunPython(create_default_accounts),
    ]
