from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from .base import BaseModel
from .product import Product
from ..choices import OrderStatus, Currency
from ..managers import OrderManager, CartManager
from ..order_management import OrderStatusTransition


class Order(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name=_('User')
    )
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.CART
    )
    currency = models.CharField(
        _('Currency'),
        max_length=3,
        choices=Currency.choices,
        default=Currency.IRR
    )
    total_amount = models.DecimalField(
        _('Total Amount'),
        max_digits=12,
        decimal_places=0,
        default=0
    )
    shipping_address = models.TextField(_('Shipping Address'))
    phone_number = models.CharField(_('Phone Number'), max_length=15)

    # Optional fields
    note = models.TextField(_('Note'), blank=True)
    tracking_code = models.CharField(_('Tracking Code'), max_length=100, blank=True)

    objects = OrderManager()
    cart_objects = CartManager()

    class Meta:
        verbose_name = _('Order')
        verbose_name_plural = _('Orders')
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.id} - {self.user.get_full_name()}"

    def calculate_total(self):
        """Calculate total amount from order items"""
        total = sum(item.total_price for item in self.items.all())
        self.total_amount = total
        self.save()
        return total

    @property
    def total_items(self):
        """Get total number of items in order"""
        result = self.items.aggregate(total=Sum('quantity'))
        return result['total'] or 0

    def product_count(self):
        return self.items.count()

    def transition_to(self, new_status: str) -> None:
        """Transition order to new status with validation"""
        OrderStatusTransition.validate_transition(self.status, new_status)
        self.status = new_status
        self.save()

    def cancel(self) -> None:
        """Cancel the order"""
        self.transition_to(OrderStatus.CANCELLED)

    def confirm_shipping(self, tracking_code: str) -> None:
        """Mark order as shipped with tracking code"""
        if not tracking_code:
            raise ValidationError(_('Tracking code is required'))
        self.tracking_code = tracking_code
        self.transition_to(OrderStatus.SHIPPED)

    def mark_delivered(self) -> None:
        """Mark order as delivered"""
        self.transition_to(OrderStatus.DELIVERED)

    def process_return(self) -> None:
        """Process order return"""
        self.transition_to(OrderStatus.RETURNED)

    def process_refund(self) -> None:
        """Process order refund"""
        self.transition_to(OrderStatus.REFUNDED)

    @property
    def can_cancel(self) -> bool:
        """Check if order can be cancelled"""
        return OrderStatus.CANCELLED in OrderStatusTransition.get_allowed_transitions(self.status)

    @property
    def can_ship(self) -> bool:
        """Check if order can be shipped"""
        return OrderStatus.SHIPPED in OrderStatusTransition.get_allowed_transitions(self.status)

    @property
    def can_deliver(self) -> bool:
        """Check if order can be marked as delivered"""
        return OrderStatus.DELIVERED in OrderStatusTransition.get_allowed_transitions(self.status)


class OrderItem(BaseModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Order')
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name=_('Product')
    )
    quantity = models.PositiveIntegerField(_('Quantity'), default=1)
    price = models.DecimalField(
        _('Price at Time of Purchase'),
        max_digits=12,
        decimal_places=0
    )

    class Meta:
        verbose_name = _('Order Item')
        verbose_name_plural = _('Order Items')
        unique_together = ['order', 'product']

    def __str__(self):
        return f"{self.quantity}x {self.product.title} in Order {self.order.id}"

    @property
    def total_price(self):
        """Calculate total price for this item"""
        return self.quantity * self.price

    def save(self, *args, **kwargs):
        # If price isn't set, use current product price
        if not self.price:
            self.price = self.product.price
        super().save(*args, **kwargs)
        # Recalculate order total
        self.order.calculate_total()


class OrderStatusHistory(BaseModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name=_('Order')
    )
    from_status = models.CharField(
        _('From Status'),
        max_length=20,
        choices=OrderStatus.choices
    )
    to_status = models.CharField(
        _('To Status'),
        max_length=20,
        choices=OrderStatus.choices
    )
    note = models.TextField(_('Note'), blank=True)

    class Meta:
        verbose_name = _('Order Status History')
        verbose_name_plural = _('Order Status Histories')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order.id}: {self.from_status} → {self.to_status}"
