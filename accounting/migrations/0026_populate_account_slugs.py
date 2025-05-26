from django.db import migrations
from django.utils.text import slugify

def populate_slugs(apps, schema_editor):
    Account = apps.get_model('accounting', 'Account')
    for account in Account.objects.all():
        if not account.slug:
            account.slug = slugify(account.name)
            account.save()

class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0008_account_slug_alter_account_name_alter_account_type'),
    ]

    operations = [
        migrations.RunPython(populate_slugs),
    ]
