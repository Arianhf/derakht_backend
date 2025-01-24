from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import BaseModel


class Product(BaseModel):
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    price = models.DecimalField(_('Price'), max_digits=12, decimal_places=0)  # Using 0 decimal places for Rial
    stock = models.PositiveIntegerField(_('Stock'), default=0)
    sku = models.CharField(_('SKU'), max_length=50, unique=True)
    is_available = models.BooleanField(_('Is Available'), default=True)

    # SEO and display fields
    slug = models.SlugField(_('Slug'), max_length=255, unique=True)
    meta_title = models.CharField(_('Meta Title'), max_length=200, blank=True)
    meta_description = models.TextField(_('Meta Description'), blank=True)

    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def is_in_stock(self):
        return self.stock > 0

    @property
    def price_in_toman(self):
        return self.price / 10


class ProductImage(BaseModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_('Product')
    )
    image = models.ImageField(_('Image'), upload_to='shop/products/')
    alt_text = models.CharField(_('Alternative Text'), max_length=200, blank=True)
    is_feature = models.BooleanField(_('Is Feature Image'), default=False)

    class Meta:
        verbose_name = _('Product Image')
        verbose_name_plural = _('Product Images')
        ordering = ['-is_feature', '-created_at']

    def __str__(self):
        return f"Image for {self.product.title}"

    def save(self, *args, **kwargs):
        if self.is_feature:
            # Set all other images of this product to not feature
            ProductImage.objects.filter(
                product=self.product,
                is_feature=True
            ).update(is_feature=False)
        super().save(*args, **kwargs)
