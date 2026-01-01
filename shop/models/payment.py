# shop/models/payment.py

from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import BaseModel
from .order import Order
from ..choices import PaymentStatus, Currency, PaymentMethodProvider


class Payment(BaseModel):
    """Model for payment records"""

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name=_("Order"),
    )
    amount = models.PositiveIntegerField(_("Amount"))
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    gateway = models.CharField(
        _("Payment Gateway"),
        max_length=20,
        choices=PaymentMethodProvider.choices,
        default=PaymentMethodProvider.ZARINPAL,
    )
    currency = models.CharField(
        _("Currency"), max_length=3, choices=Currency.choices, default=Currency.IRR
    )
    reference_id = models.CharField(
        _("Reference ID"), max_length=255, blank=True, null=True
    )
    transaction_id = models.CharField(
        _("Transaction ID"), max_length=255, blank=True, null=True
    )

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['order'], name='payment_order_idx'),
            models.Index(fields=['status', '-created_at'], name='payment_status_idx'),
        ]

    def __str__(self):
        return f"Payment {self.id} for Order {self.order.id}"


class PaymentTransaction(BaseModel):
    """Model for payment transaction records"""

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name=_("Payment"),
    )
    amount = models.PositiveIntegerField(_("Amount"))
    transaction_id = models.CharField(
        _("Transaction ID"), max_length=255, blank=True, null=True
    )
    provider_status = models.CharField(
        _("Provider Status"), max_length=100, blank=True, null=True
    )
    raw_request = models.JSONField(_("Raw Request"), blank=True, null=True)
    raw_response = models.JSONField(_("Raw Response"), blank=True, null=True)
    payment_receipt = models.ImageField(
        _("Payment Receipt"),
        upload_to="payment_receipts/%Y/%m/%d/",
        blank=True,
        null=True,
        help_text=_("Upload payment receipt for manual verification"),
    )

    class Meta:
        verbose_name = _("Payment Transaction")
        verbose_name_plural = _("Payment Transactions")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Transaction {self.id} for Payment {self.payment.id}"
