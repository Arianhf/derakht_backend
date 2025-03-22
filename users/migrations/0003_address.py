# Generated by Django 5.1.4 on 2025-03-22 16:12

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_alter_user_phone_number"),
    ]

    operations = [
        migrations.CreateModel(
            name="Address",
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
                    "recipient_name",
                    models.CharField(max_length=255, verbose_name="Recipient Name"),
                ),
                ("address", models.TextField(verbose_name="Address")),
                ("city", models.CharField(max_length=100, verbose_name="City")),
                ("province", models.CharField(max_length=100, verbose_name="Province")),
                (
                    "postal_code",
                    models.CharField(max_length=20, verbose_name="Postal Code"),
                ),
                (
                    "phone_number",
                    models.CharField(max_length=15, verbose_name="Phone Number"),
                ),
                (
                    "is_default",
                    models.BooleanField(default=False, verbose_name="Is Default"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="addresses",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "verbose_name": "Address",
                "verbose_name_plural": "Addresses",
                "ordering": ["-is_default", "-created_at"],
            },
        ),
    ]
