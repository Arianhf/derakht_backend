from django.contrib.admin.utils import quote
from django.urls import reverse
from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from django.utils.translation import gettext_lazy as _
from wagtail_modeladmin.options import ModelAdmin, ModelAdminGroup, modeladmin_register

from .models import Product, ProductImage


class ProductImageAdmin(ModelAdmin):
    model = ProductImage
    menu_label = _("Product Images")
    menu_icon = "image"
    list_display = ("thumbnail", "product", "alt_text", "is_feature")
    list_filter = ("is_feature", "created_at")
    search_fields = ("product__title", "alt_text")

    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover;" />',
                obj.image.get_rendition("fill-50x50").url,
            )
        return ""

    thumbnail.short_description = _("Thumbnail")


class ProductAdmin(ModelAdmin):
    model = Product
    menu_label = _("Products")
    menu_icon = "package"
    menu_order = 100
    list_display = (
        "title",
        "price_display",
        "age_range_admin",
        "stock",
        "is_available",
        "created_at",
        "view_images",
    )
    list_filter = ("is_available", "created_at")
    search_fields = ("title", "description", "sku")

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("title"),
                FieldPanel("description"),
                FieldPanel("slug"),
            ],
            heading=_("Basic Information"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("price"),
                FieldPanel("stock"),
                FieldPanel("sku"),
                FieldPanel("is_available"),
            ],
            heading=_("Pricing and Inventory"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("min_age"),
                FieldPanel("max_age"),
            ],
            heading=_("Age Range"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("meta_title"),
                FieldPanel("meta_description"),
            ],
            heading=_("SEO"),
        ),
    ]

    def price_display(self, obj):
        return f"{obj.price:,} IRR ({obj.price_in_toman:,} IRT)"

    price_display.short_description = _("Price")

    def age_range_admin(self, obj):
        return obj.age_range or _("All Ages")

    age_range_admin.short_description = _("Age Range")

    def view_images(self, obj):
        """Add a link to filter the ProductImage admin to show only images for this product"""
        count = obj.images.count()
        url = reverse("wagtailadmin_explore_root")  # Base Wagtail admin URL
        filter_url = f"{url}?product__id__exact={quote(obj.pk)}"
        return format_html('<a href="{}">{} {}</a>', filter_url, count, _("image(s)"))

    view_images.short_description = _("Images")


class ShopGroup(ModelAdminGroup):
    menu_label = _("Shop")
    menu_icon = "shopping-cart"
    menu_order = 200
    items = (
        ProductAdmin,
        ProductImageAdmin,
    )


modeladmin_register(ShopGroup)


@hooks.register("insert_global_admin_css")
def product_image_preview_css():
    return format_html(
        "<style>"
        ".product-image-preview {{ max-width: 150px; max-height: 150px; margin: 10px 0; }}"
        "</style>"
    )
