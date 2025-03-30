# Generated by Django 5.1.7 on 2025-03-28 19:14

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0005_remove_order_shipping_address"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name="payment",
            name="payment_type",
        ),
        migrations.RemoveField(
            model_name="payment",
            name="provider",
        ),
        migrations.RemoveField(
            model_name="paymenttransaction",
            name="provider_message",
        ),
        migrations.RemoveField(
            model_name="paymenttransaction",
            name="provider_tracking_code",
        ),
        migrations.AddField(
            model_name="payment",
            name="gateway",
            field=models.CharField(
                choices=[("ZARINPAL", "Zarinpal")],
                default="ZARINPAL",
                max_length=20,
                verbose_name="Payment Gateway",
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="transaction_id",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Transaction ID"
            ),
        ),
        migrations.AddField(
            model_name="paymenttransaction",
            name="raw_request",
            field=models.JSONField(blank=True, null=True, verbose_name="Raw Request"),
        ),
        migrations.AlterField(
            model_name="payment",
            name="amount",
            field=models.PositiveIntegerField(verbose_name="Amount"),
        ),
        migrations.AlterField(
            model_name="payment",
            name="reference_id",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Reference ID"
            ),
        ),
        migrations.AlterField(
            model_name="paymenttransaction",
            name="amount",
            field=models.PositiveIntegerField(verbose_name="Amount"),
        ),
        migrations.AlterField(
            model_name="paymenttransaction",
            name="payment",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="transactions",
                to="shop.payment",
                verbose_name="Payment",
            ),
        ),
        migrations.AlterField(
            model_name="paymenttransaction",
            name="provider_status",
            field=models.CharField(
                blank=True, max_length=100, null=True, verbose_name="Provider Status"
            ),
        ),
        migrations.AlterField(
            model_name="paymenttransaction",
            name="raw_response",
            field=models.JSONField(blank=True, null=True, verbose_name="Raw Response"),
        ),
        migrations.AlterField(
            model_name="paymenttransaction",
            name="transaction_id",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Transaction ID"
            ),
        ),
        migrations.CreateModel(
            name="Cart",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "anonymous_id",
                    models.UUIDField(
                        blank=True,
                        db_index=True,
                        null=True,
                        verbose_name="Anonymous Cart ID",
                    ),
                ),
                (
                    "last_activity",
                    models.DateTimeField(auto_now=True, verbose_name="Last Activity"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="carts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "verbose_name": "Cart",
                "verbose_name_plural": "Carts",
            },
        ),
        migrations.AlterUniqueTogether(
            name="cartitem",
            unique_together=set(),
        ),
        migrations.AddField(
            model_name="cartitem",
            name="cart",
            field=models.ForeignKey(
                default="",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="items",
                to="shop.cart",
                verbose_name="Cart",
            ),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name="cartitem",
            unique_together={("cart", "product")},
        ),
        migrations.AddConstraint(
            model_name="cart",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("user__isnull", False),
                    ("anonymous_id__isnull", False),
                    _connector="OR",
                ),
                name="cart_must_have_user_or_anonymous_id",
            ),
        ),
        migrations.RemoveField(
            model_name="cartitem",
            name="user",
        ),
    ]
