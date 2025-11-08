# Generated manually for manual payment verification flow

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0007_productinfopage"),
    ]

    operations = [
        # Add payment_receipt field to PaymentTransaction model
        migrations.AddField(
            model_name="paymenttransaction",
            name="payment_receipt",
            field=models.ImageField(
                blank=True,
                help_text="Upload payment receipt for manual verification",
                null=True,
                upload_to="payment_receipts/%Y/%m/%d/",
                verbose_name="Payment Receipt",
            ),
        ),
        # Update gateway choices to include MANUAL
        migrations.AlterField(
            model_name="payment",
            name="gateway",
            field=models.CharField(
                choices=[
                    ("ZARINPAL", "Zarinpal"),
                    ("MANUAL", "Manual Transfer"),
                ],
                default="ZARINPAL",
                max_length=20,
                verbose_name="Payment Gateway",
            ),
        ),
        # Update order status choices to include AWAITING_VERIFICATION
        migrations.AlterField(
            model_name="order",
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
                default="CART",
                max_length=25,
                verbose_name="Status",
            ),
        ),
    ]
