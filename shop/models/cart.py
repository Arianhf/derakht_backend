# shop/models/cart.py

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from .base import BaseModel
from .product import Product


class CartItem(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name=_("User"),
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
        unique_together = ["user", "product"]

    def __str__(self):
        return f"{self.quantity}x {self.product.title} - {self.user.email}"

    @property
    def price(self):
        return self.product.price

    @property
    def total_price(self):
        return self.product.price * self.quantity
