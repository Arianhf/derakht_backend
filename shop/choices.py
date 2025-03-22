from django.db import models
from django.utils.translation import gettext_lazy as _


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    PROCESSING = "PROCESSING", _("Processing")
    COMPLETED = "COMPLETED", _("Completed")
    FAILED = "FAILED", _("Failed")
    REFUNDED = "REFUNDED", _("Refunded")
    CANCELLED = "CANCELLED", _("Cancelled")


class OrderStatus(models.TextChoices):
    CART = "CART", _("Cart")  # Initial state when order is just a cart
    PENDING = "PENDING", _("Pending")  # Order placed but payment not initiated
    PROCESSING = "PROCESSING", _("Processing")  # Payment in progress
    CONFIRMED = "CONFIRMED", _("Confirmed")  # Payment completed, order confirmed
    SHIPPED = "SHIPPED", _("Shipped")
    DELIVERED = "DELIVERED", _("Delivered")
    CANCELLED = "CANCELLED", _("Cancelled")
    REFUNDED = "REFUNDED", _("Refunded")
    RETURNED = "RETURNED", _("Returned")


class PaymentType(models.TextChoices):
    ONLINE = "ONLINE", _("Online")
    CREDIT = "CREDIT", _("Credit")
    CASH_ON_DELIVERY = "CASH_ON_DELIVERY", _("Cash on Delivery")


class Currency(models.TextChoices):
    IRR = "IRR", _("Iranian Rial")
    IRT = "IRT", _("Iranian Toman")


class IPGProvider(models.TextChoices):
    ZARINPAL = "ZARINPAL", _("Zarinpal")
    MELLAT = "MELLAT", _("Mellat")
    SAMAN = "SAMAN", _("Saman")
    PARSIAN = "PARSIAN", _("Parsian")
