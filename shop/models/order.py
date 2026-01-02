from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from .base import BaseModel
from .product import Product
from ..choices import OrderStatus, Currency, ShippingMethod
from ..managers import OrderManager, CartManager
from ..order_management import OrderStatusTransition
from users.validators import validate_iranian_phone, validate_iranian_postal_code


class Order(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name=_("User"),
    )
    status = models.CharField(
        _("Status"),
        max_length=25,
        choices=OrderStatus.choices,
        default=OrderStatus.CART,
    )
    currency = models.CharField(
        _("Currency"), max_length=3, choices=Currency.choices, default=Currency.IRR
    )
    total_amount = models.PositiveIntegerField(_("Total Amount"))
    phone_number = models.CharField(
        _("Phone Number"),
        max_length=15,
        validators=[validate_iranian_phone]
    )
    notes = models.TextField(_("Notes"), blank=True, null=True)
    tracking_code = models.CharField(_("Tracking Code"), max_length=100, blank=True)
    shipping_method = models.CharField(
        _("Shipping Method"),
        max_length=25,
        choices=ShippingMethod.choices,
        blank=True,
        null=True,
    )
    shipping_cost = models.PositiveIntegerField(_("Shipping Cost"), default=0)

    objects = OrderManager()
    cart_objects = CartManager()

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['user', 'status', '-created_at'], name='order_user_status_idx'),
            models.Index(fields=['status', '-created_at'], name='order_status_idx'),
        ]

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
        result = self.items.aggregate(total=Sum("quantity"))
        return result["total"] or 0

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
            raise ValidationError(_("Tracking code is required"))
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
        return OrderStatus.CANCELLED in OrderStatusTransition.get_allowed_transitions(
            self.status
        )

    @property
    def can_ship(self) -> bool:
        """Check if order can be shipped"""
        return OrderStatus.SHIPPED in OrderStatusTransition.get_allowed_transitions(
            self.status
        )

    @property
    def can_deliver(self) -> bool:
        """Check if order can be marked as delivered"""
        return OrderStatus.DELIVERED in OrderStatusTransition.get_allowed_transitions(
            self.status
        )

    @property
    def shipping_address(self):
        return self.shipping_info.full_address


class OrderItem(BaseModel):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items", verbose_name=_("Order")
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name=_("Product"),
    )
    quantity = models.PositiveIntegerField(_("Quantity"), default=1)
    price = models.PositiveIntegerField(_("Price at Time of Purchase"))

    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")
        unique_together = ["order", "product"]

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


class ShippingInfo(BaseModel):
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="shipping_info",
        verbose_name=_("Order"),
    )
    address = models.TextField(_("Address"))
    city = models.CharField(_("City"), max_length=100)
    province = models.CharField(_("Province"), max_length=100)
    postal_code = models.CharField(
        _("Postal Code"),
        max_length=20,
        validators=[validate_iranian_postal_code]
    )
    recipient_name = models.CharField(_("Recipient Name"), max_length=255)
    phone_number = models.CharField(
        _("Phone Number"),
        max_length=15,
        validators=[validate_iranian_phone]
    )

    class Meta:
        verbose_name = _("Shipping Information")
        verbose_name_plural = _("Shipping Information")

    def __str__(self):
        return f"Shipping info for Order {self.order.id}"

    @property
    def full_address(self):
        return f"{self.address}, {self.city}, {self.province}, {self.postal_code}, {self.recipient_name}, {self.phone_number}"


class PaymentInfo(BaseModel):
    PAYMENT_METHOD_CHOICES = [
        ("online", _("Online Payment")),
        ("cash", _("Cash on Delivery")),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("completed", _("Completed")),
        ("failed", _("Failed")),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="payment_info",
        verbose_name=_("Order"),
    )
    method = models.CharField(
        _("Payment Method"), max_length=20, choices=PAYMENT_METHOD_CHOICES
    )
    transaction_id = models.CharField(
        _("Transaction ID"), max_length=255, blank=True, null=True
    )
    payment_date = models.DateTimeField(_("Payment Date"), blank=True, null=True)
    status = models.CharField(
        _("Status"), max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending"
    )

    class Meta:
        verbose_name = _("Payment Information")
        verbose_name_plural = _("Payment Information")

    def __str__(self):
        return f"Payment for Order {self.order.id}"


class OrderStatusHistory(BaseModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history",
        verbose_name=_("Order"),
    )
    from_status = models.CharField(
        _("From Status"), max_length=25, choices=OrderStatus.choices
    )
    to_status = models.CharField(
        _("To Status"), max_length=25, choices=OrderStatus.choices
    )
    note = models.TextField(_("Note"), blank=True)

    class Meta:
        verbose_name = _("Order Status History")
        verbose_name_plural = _("Order Status Histories")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order.id}: {self.from_status} → {self.to_status}"
