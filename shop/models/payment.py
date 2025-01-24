from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import BaseModel
from .order import Order
from ..choices import PaymentStatus, PaymentType, IPGProvider, Currency


class Payment(BaseModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name=_('Order')
    )
    amount = models.DecimalField(
        _('Amount'),
        max_digits=12,
        decimal_places=0
    )
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    payment_type = models.CharField(
        _('Payment Type'),
        max_length=20,
        choices=PaymentType.choices,
        default=PaymentType.ONLINE
    )
    provider = models.CharField(
        _('Payment Provider'),
        max_length=20,
        choices=IPGProvider.choices,
        default=IPGProvider.ZARINPAL
    )
    currency = models.CharField(
        _('Currency'),
        max_length=3,
        choices=Currency.choices,
        default=Currency.IRR
    )
    reference_id = models.CharField(
        _('Reference ID'),
        max_length=255,
        blank=True,
        help_text=_('Payment reference ID from the payment provider')
    )

    class Meta:
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.id} for Order {self.order.id}"


class PaymentTransaction(BaseModel):
    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name=_('Payment')
    )
    amount = models.DecimalField(
        _('Amount'),
        max_digits=12,
        decimal_places=0
    )
    transaction_id = models.CharField(
        _('Transaction ID'),
        max_length=255,
        unique=True,
        null=True,
        blank=True
    )
    provider_tracking_code = models.CharField(
        _('Provider Tracking Code'),
        max_length=255,
        blank=True
    )
    provider_status = models.CharField(
        _('Provider Status'),
        max_length=100,
        blank=True
    )
    provider_message = models.TextField(
        _('Provider Message'),
        blank=True
    )
    raw_response = models.JSONField(
        _('Raw Response'),
        blank=True,
        null=True,
        help_text=_('Complete response from payment provider')
    )

    class Meta:
        verbose_name = _('Payment Transaction')
        verbose_name_plural = _('Payment Transactions')
        ordering = ['-created_at']

    def __str__(self):
        return f"Transaction {self.transaction_id} for Payment {self.payment.id}"
