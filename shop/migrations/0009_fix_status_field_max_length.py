# Generated manually to fix status field max_length

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0008_add_manual_payment_support"),
    ]

    operations = [
        # Update Invoice.status max_length
        migrations.AlterField(
            model_name="invoice",
            name="status",
            field=models.CharField(
                choices=[
                    ("CART", "Cart"),
                    ("PENDING", "Pending"),
                    ("AWAITING_VERIFICATION", "Awaiting Verification"),
                    ("PROCESSING", "Processing"),
                    ("CONFIRMED", "Confirmed"),
                    ("SHIPPED", "Shipped"),
                    ("DELIVERED", "Delivered"),
                    ("CANCELLED", "Cancelled"),
                    ("REFUNDED", "Refunded"),
                    ("RETURNED", "Returned"),
                ],
                max_length=25,
                verbose_name="Status",
            ),
        ),
        # Update OrderStatusHistory.from_status max_length
        migrations.AlterField(
            model_name="orderstatushistory",
            name="from_status",
            field=models.CharField(
                choices=[
                    ("CART", "Cart"),
                    ("PENDING", "Pending"),
                    ("AWAITING_VERIFICATION", "Awaiting Verification"),
                    ("PROCESSING", "Processing"),
                    ("CONFIRMED", "Confirmed"),
                    ("SHIPPED", "Shipped"),
                    ("DELIVERED", "Delivered"),
                    ("CANCELLED", "Cancelled"),
                    ("REFUNDED", "Refunded"),
                    ("RETURNED", "Returned"),
                ],
                max_length=25,
                verbose_name="From Status",
            ),
        ),
        # Update OrderStatusHistory.to_status max_length
        migrations.AlterField(
            model_name="orderstatushistory",
            name="to_status",
            field=models.CharField(
                choices=[
                    ("CART", "Cart"),
                    ("PENDING", "Pending"),
                    ("AWAITING_VERIFICATION", "Awaiting Verification"),
                    ("PROCESSING", "Processing"),
                    ("CONFIRMED", "Confirmed"),
                    ("SHIPPED", "Shipped"),
                    ("DELIVERED", "Delivered"),
                    ("CANCELLED", "Cancelled"),
                    ("REFUNDED", "Refunded"),
                    ("RETURNED", "Returned"),
                ],
                max_length=25,
                verbose_name="To Status",
            ),
        ),
    ]
