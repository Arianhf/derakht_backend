import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from core.logging_utils import get_logger, log_user_action
from .models import Order, OrderItem
from .models.invoice import Invoice, InvoiceItem
from .models.order import OrderStatusHistory
from .models.payment import Payment

# Initialize loggers
logger = get_logger("shop.orders")
payment_logger = get_logger("shop.payments")
audit_logger = get_logger("audit")


@receiver(post_save, sender=OrderItem)
def update_order_total(sender, instance, created, **kwargs):
    """Update order total when order items change"""
    old_total = instance.order.total_amount
    instance.order.calculate_total()

    action = "created" if created else "updated"
    logger.info(
        f"Order item {action}: {instance.id} for order {instance.order.id}",
        extra={
            "extra_data": {
                "order_item_id": str(instance.id),
                "order_id": str(instance.order.id),
                "product_id": str(instance.product.id),
                "quantity": instance.quantity,
                "price": float(instance.price),
                "old_total": float(old_total),
                "new_total": float(instance.order.total_amount),
                "action": action,
            }
        },
    )


@receiver(post_save, sender=Payment)
def handle_payment_status_change(sender, instance, **kwargs):
    """Handle order status changes based on payment status"""
    if instance.status == "COMPLETED":
        # Create invoice when payment is completed
        order = instance.order
        if not Invoice.objects.filter(order=order).exists():
            try:
                invoice = Invoice.objects.create(
                    order=order,
                    status=order.status,
                    total_amount=order.total_amount,
                    currency=order.currency,
                    shipping_address=order.shipping_address,
                    phone_number=order.phone_number,
                )
                # Create invoice items
                invoice_items_count = 0
                for order_item in order.items.all():
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        product_title=order_item.product.title,
                        product_sku=order_item.product.sku,
                        quantity=order_item.quantity,
                        price=order_item.price,
                    )
                    invoice_items_count += 1

                payment_logger.info(
                    f"Invoice created for order {order.id}",
                    extra={
                        "extra_data": {
                            "invoice_id": str(invoice.id),
                            "order_id": str(order.id),
                            "payment_id": str(instance.id),
                            "total_amount": float(order.total_amount),
                            "items_count": invoice_items_count,
                            "user_id": order.user.id,
                        }
                    },
                )

                log_user_action(
                    audit_logger,
                    "invoice_created",
                    user_id=order.user.id,
                    user_email=order.user.email,
                    extra_data={
                        "invoice_id": str(invoice.id),
                        "order_id": str(order.id),
                        "payment_id": str(instance.id),
                        "total_amount": float(order.total_amount),
                    },
                )

            except Exception as e:
                payment_logger.error(
                    f"Failed to create invoice for order {order.id}: {str(e)}",
                    extra={
                        "order_id": str(order.id),
                        "payment_id": str(instance.id),
                        "error": str(e),
                    },
                    exc_info=True,
                )


@receiver(pre_save, sender=Order)
def track_order_status_change(sender, instance, **kwargs):
    """Track order status changes"""
    if instance.pk:  # Only for existing orders
        try:
            old_order = Order.objects.get(pk=instance.pk)
            if old_order.status != instance.status:
                OrderStatusHistory.objects.create(
                    order=instance,
                    from_status=old_order.status,
                    to_status=instance.status,
                )

                logger.info(
                    f"Order status changed: {instance.id}",
                    extra={
                        "extra_data": {
                            "order_id": str(instance.id),
                            "from_status": old_order.status,
                            "to_status": instance.status,
                            "user_id": instance.user.id,
                        }
                    },
                )

                log_user_action(
                    audit_logger,
                    "order_status_changed",
                    user_id=instance.user.id,
                    user_email=instance.user.email,
                    extra_data={
                        "order_id": str(instance.id),
                        "from_status": old_order.status,
                        "to_status": instance.status,
                    },
                )

        except Order.DoesNotExist:
            pass
