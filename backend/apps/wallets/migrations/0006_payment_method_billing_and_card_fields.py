import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reference", "0003_catalogueload"),
        ("wallets", "0005_movimientobilletera_idempotency_key_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymentmethod",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("TARJETA", "Tarjeta"),
                    ("CUENTA_BANCARIA", "Cuenta bancaria"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="paymentmethod",
            name="cardholder_first_name",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="paymentmethod",
            name="cardholder_last_name",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="paymentmethod",
            name="marca",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="paymentmethod",
            name="billing_country",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="billing_payment_methods",
                to="reference.country",
            ),
        ),
        migrations.AddField(
            model_name="paymentmethod",
            name="billing_subdivision",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="billing_payment_methods",
                to="reference.subdivision",
            ),
        ),
        migrations.AddField(
            model_name="paymentmethod",
            name="billing_city",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="billing_payment_methods",
                to="reference.locality",
            ),
        ),
        migrations.AddField(
            model_name="paymentmethod",
            name="billing_address",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="paymentmethod",
            name="postal_code",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
    ]
