from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0007_user_billing_city_user_birth_city_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="phone",
            field=models.CharField(blank=True, max_length=30),
        ),
    ]
