from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import BaseModel


class Product(BaseModel):
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    price = models.DecimalField(_('Price'), max_digits=12, decimal_places=0)
    stock = models.PositiveIntegerField(_('Stock'), default=0)
    sku = models.CharField(_('SKU'), max_length=50, unique=True)
    is_available = models.BooleanField(_('Is Available'), default=True)

    # Age range fields
    min_age = models.PositiveSmallIntegerField(_('Minimum Age'), null=True, blank=True)
    max_age = models.PositiveSmallIntegerField(_('Maximum Age'), null=True, blank=True)

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

    @property
    def age_range_display(self):
        if self.min_age is not None and self.max_age is not None:
            return f"{self.min_age}-{self.max_age}"
        elif self.min_age is not None:
            return f"{self.min_age}+"
        elif self.max_age is not None:
            return f"0-{self.max_age}"
        return None

    @property
    def feature_image(self):
        feature_image = self.images.filter(is_feature=True).first()
        if not feature_image:
            # Fallback to first image if no featured image is set
            feature_image = self.images.first()
        return feature_image


class ProductImage(BaseModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_('Product')
    )
    # Use Wagtail's image model
    image = models.ForeignKey(
        'wagtailimages.Image',
        on_delete=models.CASCADE,
        related_name='+',
        verbose_name=_('Image')
    )
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
            ).exclude(id=self.id).update(is_feature=False)
        super().save(*args, **kwargs)