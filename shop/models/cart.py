# shop/models/cart.py
import uuid
from django.db import models
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from .base import BaseModel
from .product import Product
from django.conf import settings


class Cart(BaseModel):
    """
    Cart model that can be associated with a user or an anonymous ID
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carts",
        verbose_name=_("User"),
        null=True,
        blank=True,
    )
    anonymous_id = models.UUIDField(
        _("Anonymous Cart ID"), null=True, blank=True, db_index=True
    )
    last_activity = models.DateTimeField(_("Last Activity"), auto_now=True)

    class Meta:
        verbose_name = _("Cart")
        verbose_name_plural = _("Carts")
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(user__isnull=False) | models.Q(anonymous_id__isnull=False)
                ),
                name="cart_must_have_user_or_anonymous_id",
            )
        ]

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.email}"
        return f"Anonymous cart {self.anonymous_id}"

    @property
    def total_amount(self):
        """Calculate total amount of all cart items"""
        return sum(item.total_price for item in self.items.all())

    @property
    def items_count(self):
        """Get total number of items in order"""
        result = self.items.aggregate(total=Sum("quantity"))
        return result["total"] or 0


class CartItem(BaseModel):
    """
    Item in a cart
    """

    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name="items", verbose_name=_("Cart")
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name=_("Product"),
    )
    quantity = models.PositiveIntegerField(_("Quantity"), default=1)

    class Meta:
        verbose_name = _("Cart Item")
        verbose_name_plural = _("Cart Items")
        unique_together = ("cart", "product")

    def __str__(self):
        return f"{self.quantity} x {self.product.title} in cart"

    @property
    def price(self):
        return self.product.price

    @property
    def total_price(self):
        """Calculate total price for this item"""
        return self.quantity * self.product.price
