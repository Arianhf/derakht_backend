# shop/models/product.py
from django.db import models
from django.utils.translation import gettext_lazy as _

from wagtail.admin.panels import FieldPanel
from wagtail.api import APIField
from wagtail.fields import RichTextField
from wagtail.models import Page

from blog.serializers import RichTextField as RichTextFieldSerializer
from .base import BaseModel


class Product(BaseModel):
    title = models.CharField(_("Title"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    price = models.DecimalField(_("Price"), max_digits=12, decimal_places=0)
    stock = models.PositiveIntegerField(_("Stock"), default=0)
    sku = models.CharField(_("SKU"), max_length=50, unique=True)
    is_available = models.BooleanField(_("Is Available"), default=True)

    # Age range fields
    min_age = models.PositiveSmallIntegerField(_("Minimum Age"), blank=True, null=True)
    max_age = models.PositiveSmallIntegerField(_("Maximum Age"), blank=True, null=True)

    # SEO and display fields
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    meta_title = models.CharField(_("Meta Title"), max_length=200, blank=True)
    meta_description = models.TextField(_("Meta Description"), blank=True)

    # Category relation
    category = models.ForeignKey(
        "Category",
        on_delete=models.SET_NULL,
        related_name="products",
        verbose_name=_("Category"),
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def is_in_stock(self):
        return self.stock > 0

    @property
    def price_in_toman(self):
        return int(self.price / 10)

    @property
    def age_range(self):
        if self.min_age and self.max_age:
            return f"{self.min_age}-{self.max_age} سال"
        elif self.min_age:
            return f"{self.min_age}+ سال"
        return ""

    @property
    def feature_image(self):
        feature_image = self.images.filter(is_feature=True).first()
        if not feature_image and self.images.exists():
            # Fallback to first image if no featured image is set
            feature_image = self.images.first()
        else:
            feature_image = None
        return feature_image


class ProductImage(BaseModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("Product"),
    )
    # Use Wagtail's image model
    image = models.ForeignKey(
        "wagtailimages.Image",
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name=_("Image"),
    )
    alt_text = models.CharField(_("Alternative Text"), max_length=200, blank=True)
    is_feature = models.BooleanField(_("Is Feature Image"), default=False)

    class Meta:
        verbose_name = _("Product Image")
        verbose_name_plural = _("Product Images")
        ordering = ["-is_feature", "-created_at"]

    def __str__(self):
        return f"Image for {self.product.title}"

    def save(self, *args, **kwargs):
        if self.is_feature:
            # Set all other images of this product to not feature
            ProductImage.objects.filter(product=self.product, is_feature=True).exclude(
                id=self.id
            ).update(is_feature=False)
        super().save(*args, **kwargs)


class ProductInfoPage(Page):
    product_code = models.CharField(
        max_length=50, help_text="Product code for QR code generation"
    )
    intro = models.CharField(max_length=250)

    # Use RichTextField for regular text content
    body = RichTextField(blank=True)

    product_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    content_panels = Page.content_panels + [
        FieldPanel("product_code"),
        FieldPanel("intro"),
        FieldPanel("product_image"),
        FieldPanel("body"),
    ]

    api_fields = [
        APIField("product_code"),
        APIField("intro"),
        APIField("product_image"),
        APIField("body", serializer=RichTextFieldSerializer()),
    ]
