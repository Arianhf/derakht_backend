from django.contrib.admin.utils import quote
from django.urls import reverse, path
from django.utils.html import format_html
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
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
        "is_visible",
        "created_at",
        "view_images",
        "duplicate_button",
    )
    list_filter = ("is_available", "is_visible", "created_at")
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
                FieldPanel("is_visible"),
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
        return f"{obj.price:,} IRT"

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

    def duplicate_button(self, obj):
        """Add a duplicate button for each product"""
        url = reverse("duplicate_product", args=[obj.pk])
        return format_html(
            '<a href="{}" class="button button-small" style="margin: 0 5px;">{}</a>',
            url,
            _("Duplicate"),
        )

    duplicate_button.short_description = _("Actions")


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


def duplicate_product_view(request, product_id):
    """View to duplicate a product with all its images"""
    from django.utils.text import slugify
    import uuid

    # Get the original product
    original_product = get_object_or_404(Product, pk=product_id)

    # Store original images before duplication
    original_images = list(original_product.images.all())

    # Create a copy of the product
    original_product.pk = None  # This will create a new instance when saved
    original_product.id = None

    # Generate unique slug - append "-copy" and a number if needed
    base_slug = f"{original_product.slug}-copy"
    new_slug = base_slug
    counter = 1
    while Product.objects.filter(slug=new_slug).exists():
        new_slug = f"{base_slug}-{counter}"
        counter += 1
    original_product.slug = new_slug

    # Generate unique SKU - append "-COPY" and a number if needed
    base_sku = f"{original_product.sku}-COPY"
    new_sku = base_sku
    counter = 1
    while Product.objects.filter(sku=new_sku).exists():
        new_sku = f"{base_sku}-{counter}"
        counter += 1
    original_product.sku = new_sku

    # Update title to indicate it's a copy
    original_product.title = f"{original_product.title} (Copy)"

    # Save the new product
    original_product.save()

    # Duplicate all images
    for image in original_images:
        ProductImage.objects.create(
            product=original_product,
            image=image.image,  # Reuse the same Wagtail image
            alt_text=image.alt_text,
            is_feature=image.is_feature,
        )

    messages.success(
        request,
        _('Product "{}" has been successfully duplicated as "{}".').format(
            original_product.title.replace(" (Copy)", ""), original_product.title
        ),
    )

    # Redirect to the product list
    return redirect("wagtailadmin_explore_root")


@hooks.register("register_admin_urls")
def register_duplicate_product_url():
    """Register the duplicate product URL"""
    return [
        path(
            "shop/product/duplicate/<str:product_id>/",
            duplicate_product_view,
            name="duplicate_product",
        ),
    ]
