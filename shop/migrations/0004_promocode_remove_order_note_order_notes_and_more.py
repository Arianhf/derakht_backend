# Generated by Django 5.1.4 on 2025-03-22 04:21

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0003_alter_productimage_image"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PromoCode",
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
                (
                    "code",
                    models.CharField(max_length=50, unique=True, verbose_name="Code"),
                ),
                (
                    "discount_type",
                    models.CharField(
                        choices=[
                            ("fixed", "Fixed Amount"),
                            ("percentage", "Percentage"),
                        ],
                        max_length=20,
                        verbose_name="Discount Type",
                    ),
                ),
                (
                    "discount_value",
                    models.PositiveIntegerField(verbose_name="Discount Value"),
                ),
                (
                    "min_purchase",
                    models.PositiveIntegerField(
                        default=0, verbose_name="Minimum Purchase"
                    ),
                ),
                (
                    "max_discount",
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name="Maximum Discount"
                    ),
                ),
                ("valid_from", models.DateTimeField(verbose_name="Valid From")),
                ("valid_to", models.DateTimeField(verbose_name="Valid To")),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Is Active"),
                ),
                (
                    "max_uses",
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name="Maximum Uses"
                    ),
                ),
                (
                    "used_count",
                    models.PositiveIntegerField(default=0, verbose_name="Used Count"),
                ),
            ],
            options={
                "verbose_name": "Promo Code",
                "verbose_name_plural": "Promo Codes",
            },
        ),
        migrations.RemoveField(
            model_name="order",
            name="note",
        ),
        migrations.AddField(
            model_name="order",
            name="notes",
            field=models.TextField(blank=True, null=True, verbose_name="Notes"),
        ),
        migrations.AlterField(
            model_name="order",
            name="total_amount",
            field=models.PositiveIntegerField(verbose_name="Total Amount"),
        ),
        migrations.AlterField(
            model_name="orderitem",
            name="price",
            field=models.PositiveIntegerField(verbose_name="Price at Time of Purchase"),
        ),
        migrations.CreateModel(
            name="Category",
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
                ("name", models.CharField(max_length=255, verbose_name="Name")),
                (
                    "slug",
                    models.SlugField(max_length=255, unique=True, verbose_name="Slug"),
                ),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="Description"),
                ),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to="categories/",
                        verbose_name="Image",
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="children",
                        to="shop.category",
                        verbose_name="Parent Category",
                    ),
                ),
            ],
            options={
                "verbose_name": "Category",
                "verbose_name_plural": "Categories",
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="product",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="products",
                to="shop.category",
                verbose_name="Category",
            ),
        ),
        migrations.CreateModel(
            name="PaymentInfo",
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
                    "method",
                    models.CharField(
                        choices=[
                            ("online", "Online Payment"),
                            ("cash", "Cash on Delivery"),
                        ],
                        max_length=20,
                        verbose_name="Payment Method",
                    ),
                ),
                (
                    "transaction_id",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        verbose_name="Transaction ID",
                    ),
                ),
                (
                    "payment_date",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Payment Date"
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment_info",
                        to="shop.order",
                        verbose_name="Order",
                    ),
                ),
            ],
            options={
                "verbose_name": "Payment Information",
                "verbose_name_plural": "Payment Information",
            },
        ),
        migrations.CreateModel(
            name="ShippingInfo",
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
                ("address", models.TextField(verbose_name="Address")),
                ("city", models.CharField(max_length=100, verbose_name="City")),
                ("province", models.CharField(max_length=100, verbose_name="Province")),
                (
                    "postal_code",
                    models.CharField(max_length=20, verbose_name="Postal Code"),
                ),
                (
                    "recipient_name",
                    models.CharField(max_length=255, verbose_name="Recipient Name"),
                ),
                (
                    "phone_number",
                    models.CharField(max_length=15, verbose_name="Phone Number"),
                ),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="shipping_info",
                        to="shop.order",
                        verbose_name="Order",
                    ),
                ),
            ],
            options={
                "verbose_name": "Shipping Information",
                "verbose_name_plural": "Shipping Information",
            },
        ),
        migrations.CreateModel(
            name="CartItem",
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
                    "quantity",
                    models.PositiveIntegerField(default=1, verbose_name="Quantity"),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cart_items",
                        to="shop.product",
                        verbose_name="Product",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cart_items",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "verbose_name": "Cart Item",
                "verbose_name_plural": "Cart Items",
                "unique_together": {("user", "product")},
            },
        ),
    ]
