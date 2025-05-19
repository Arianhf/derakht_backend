from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    Product,
    ProductImage,
    Order,
    OrderItem,
    PromoCode,
    PaymentInfo,
    ShippingInfo,
    Category,
    CartItem,
    Cart,
)
from .models.invoice import InvoiceItem, Invoice
from .models.payment import PaymentTransaction, Payment


class PaymentTransactionInline(admin.TabularInline):
    model = PaymentTransaction
    extra = 0
    readonly_fields = ["created_at"]


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ["product_title", "product_sku", "quantity", "price"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "order", "total_amount", "status", "created_at"]
    list_filter = ["status", "currency", "created_at"]
    search_fields = ["invoice_number", "order__id", "phone_number"]
    readonly_fields = ["invoice_number", "created_at", "updated_at"]
    inlines = [InvoiceItemInline]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "order",
                    "invoice_number",
                    "status",
                    "total_amount",
                    "currency",
                )
            },
        ),
        (_("Contact Information"), {"fields": ("phone_number", "shipping_address")}),
        (_("Files"), {"fields": ("pdf_file",)}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "alt_text", "is_feature", "image_preview")
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" />', obj.image.url
            )
        return "No Image"

    image_preview.short_description = _("Preview")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent")
    list_filter = ("parent",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "price", "total_price")
    list_filter = ("created_at",)
    search_fields = ("product__title",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "price")
    raw_id_fields = ["product"]


class ShippingInfoInline(admin.StackedInline):
    model = ShippingInfo
    can_delete = False


class PaymentInfoInline(admin.StackedInline):
    model = PaymentInfo
    can_delete = False


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "discount_type",
        "discount_value",
        "is_active",
        "valid_from",
        "valid_to",
        "used_count",
    )
    list_filter = ("is_active", "discount_type", "valid_from", "valid_to")
    search_fields = ("code",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "status", "total_amount", "created_at"]
    list_filter = ["status", "currency", "created_at"]
    search_fields = ["id", "user__email", "phone_number"]
    readonly_fields = ["created_at", "updated_at", "total_amount"]
    inlines = [OrderItemInline, ShippingInfoInline, PaymentInfoInline]
    fieldsets = (
        (None, {"fields": ("user", "status", "currency", "total_amount")}),
        (_("Contact Information"), {"fields": ("phone_number",)}),
        (
            _("Additional Information"),
            {"fields": ("notes", "tracking_code"), "classes": ("collapse",)},
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    actions = ["cancel_orders", "mark_orders_shipped", "mark_orders_delivered"]

    def cancel_orders(self, request, queryset):
        for order in queryset:
            if order.can_cancel:
                try:
                    order.cancel()
                except ValidationError as e:
                    messages.error(
                        request, f"Error cancelling order {order.id}: {str(e)}"
                    )
            else:
                messages.warning(
                    request,
                    f"Order {order.id} cannot be cancelled in its current state.",
                )

    cancel_orders.short_description = _("Cancel selected orders")

    def mark_orders_shipped(self, request, queryset):
        # This is simplified - you might want to add a form for tracking codes
        for order in queryset:
            if order.can_ship:
                try:
                    order.confirm_shipping(f"TRACK-{order.id}")
                except ValidationError as e:
                    messages.error(
                        request, f"Error shipping order {order.id}: {str(e)}"
                    )
            else:
                messages.warning(
                    request,
                    f"Order {order.id} cannot be marked as shipped in its current state.",
                )

    mark_orders_shipped.short_description = _("Mark selected orders as shipped")

    def mark_orders_delivered(self, request, queryset):
        for order in queryset:
            if order.can_deliver:
                try:
                    order.mark_delivered()
                except ValidationError as e:
                    messages.error(
                        request,
                        f"Error marking order {order.id} as delivered: {str(e)}",
                    )
            else:
                messages.warning(
                    request,
                    f"Order {order.id} cannot be marked as delivered in its current state.",
                )

    mark_orders_delivered.short_description = _("Mark selected orders as delivered")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "amount", "status", "created_at"]
    list_filter = ["status", "gateway", "created_at"]
    search_fields = ["order__id", "reference_id"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [PaymentTransactionInline]
    fieldsets = (
        (None, {"fields": ("order", "amount", "status", "currency")}),
        (
            _("Payment Details"),
            {"fields": ("gateway", "reference_id")},
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "price_display",
        "age_range_admin",
        "stock",
        "is_available",
        "created_at",
    )
    list_filter = ("is_available", "created_at")
    search_fields = ("title", "description", "sku")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [
        ProductImageInline,
    ]
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (_("Basic Information"), {"fields": ("title", "description", "slug")}),
        (
            _("Pricing and Inventory"),
            {"fields": ("price", "stock", "sku", "is_available")},
        ),
        (_("Age Range"), {"fields": ("min_age", "max_age")}),
        (
            _("SEO"),
            {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)},
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def price_display(self, obj):
        return f"{obj.price:,} IRT)"

    price_display.short_description = _("Price")

    def age_range_admin(self, obj):
        return obj.age_range or _("All Ages")

    age_range_admin.short_description = _("Age Range")


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ("product", "quantity", "price", "total_price")
    raw_id_fields = ["product"]

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "anonymous_id", "items_count", "total_amount", "last_activity"]
    list_filter = ["created_at", "last_activity"]
    search_fields = ["user__email", "anonymous_id"]
    readonly_fields = ["created_at", "updated_at", "anonymous_id", "total_amount", "items_count"]
    inlines = [CartItemInline]
    fieldsets = (
        (None, {"fields": ("user", "anonymous_id")}),
        (_("Cart Information"), {"fields": ("total_amount", "items_count")}),
        (_("Timestamps"), {"fields": ("last_activity", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def total_amount(self, obj):
        return obj.total_amount
    total_amount.short_description = _("Total Amount")