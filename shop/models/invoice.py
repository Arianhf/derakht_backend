from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import BaseModel
from .order import Order
from ..choices import OrderStatus, Currency


class Invoice(BaseModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name=_('Order')
    )
    status = models.CharField(
        _('Status'),
        max_length=25,
        choices=OrderStatus.choices
    )
    total_amount = models.DecimalField(
        _('Total Amount'),
        max_digits=12,
        decimal_places=0
    )
    currency = models.CharField(
        _('Currency'),
        max_length=3,
        choices=Currency.choices,
        default=Currency.IRR
    )
    shipping_address = models.TextField(_('Shipping Address'))
    phone_number = models.CharField(_('Phone Number'), max_length=15)

    # PDF generation and storage
    invoice_number = models.CharField(
        _('Invoice Number'),
        max_length=50,
        unique=True
    )
    pdf_file = models.FileField(
        _('PDF File'),
        upload_to='invoices/pdfs/',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
        ordering = ['-created_at']

    def __str__(self):
        return f"Invoice {self.invoice_number}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate invoice number - you might want to customize this
            last_invoice = Invoice.objects.order_by('-created_at').first()
            if last_invoice:
                last_number = int(last_invoice.invoice_number[3:])
                self.invoice_number = f'INV{str(last_number + 1).zfill(6)}'
            else:
                self.invoice_number = 'INV000001'
        super().save(*args, **kwargs)


class InvoiceItem(BaseModel):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='items',
        verbose_name=_('Invoice')
    )
    product_title = models.CharField(_('Product Title'), max_length=200)
    product_sku = models.CharField(_('Product SKU'), max_length=50)
    quantity = models.PositiveIntegerField(_('Quantity'))
    price = models.DecimalField(
        _('Price'),
        max_digits=12,
        decimal_places=0
    )

    class Meta:
        verbose_name = _('Invoice Item')
        verbose_name_plural = _('Invoice Items')

    def __str__(self):
        return f"{self.quantity}x {self.product_title} in Invoice {self.invoice.invoice_number}"

    @property
    def total_price(self):
        return self.quantity * self.price
