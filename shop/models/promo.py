# shop/models/promo.py

from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import BaseModel


class PromoCode(BaseModel):
    DISCOUNT_TYPE_CHOICES = [
        ("fixed", _("Fixed Amount")),
        ("percentage", _("Percentage")),
    ]

    code = models.CharField(_("Code"), max_length=50, unique=True)
    discount_type = models.CharField(
        _("Discount Type"), max_length=20, choices=DISCOUNT_TYPE_CHOICES
    )
    discount_value = models.PositiveIntegerField(_("Discount Value"))
    min_purchase = models.PositiveIntegerField(_("Minimum Purchase"), default=0)
    max_discount = models.PositiveIntegerField(
        _("Maximum Discount"), blank=True, null=True
    )
    valid_from = models.DateTimeField(_("Valid From"))
    valid_to = models.DateTimeField(_("Valid To"))
    is_active = models.BooleanField(_("Is Active"), default=True)
    max_uses = models.PositiveIntegerField(_("Maximum Uses"), blank=True, null=True)
    used_count = models.PositiveIntegerField(_("Used Count"), default=0)

    class Meta:
        verbose_name = _("Promo Code")
        verbose_name_plural = _("Promo Codes")

    def __str__(self):
        return self.code
