from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Order, OrderItem, Payment, Invoice, InvoiceItem
from .models.order import OrderStatusHistory


@receiver(post_save, sender=OrderItem)
def update_order_total(sender, instance, created, **kwargs):
    """Update order total when order items change"""
    instance.order.calculate_total()


@receiver(post_save, sender=Payment)
def handle_payment_status_change(sender, instance, **kwargs):
    """Handle order status changes based on payment status"""
    if instance.status == 'COMPLETED':
        # Create invoice when payment is completed
        order = instance.order
        if not Invoice.objects.filter(order=order).exists():
            invoice = Invoice.objects.create(
                order=order,
                status=order.status,
                total_amount=order.total_amount,
                currency=order.currency,
                shipping_address=order.shipping_address,
                phone_number=order.phone_number
            )
            # Create invoice items
            for order_item in order.items.all():
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product_title=order_item.product.title,
                    product_sku=order_item.product.sku,
                    quantity=order_item.quantity,
                    price=order_item.price
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
                    to_status=instance.status
                )
        except Order.DoesNotExist:
            pass
