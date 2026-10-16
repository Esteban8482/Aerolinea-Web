from django.db import migrations


def create_missing_wallets(apps, schema_editor):
    User = apps.get_model("users", "User")
    Wallet = apps.get_model("wallets", "Wallet")
    alias = schema_editor.connection.alias
    for user_id in User.objects.using(alias).values_list("pk", flat=True).iterator():
        Wallet.objects.using(alias).get_or_create(user_id=user_id)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_user_profile_and_identifiers"),
        ("wallets", "0001_initial"),
    ]
    operations = [migrations.RunPython(create_missing_wallets)]
