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
from .choices import PaymentStatus, OrderStatus


class PaymentTransactionInline(admin.TabularInline):
    model = PaymentTransaction
    extra = 0
    readonly_fields = ["created_at", "receipt_preview"]
    fields = ["amount", "transaction_id", "provider_status", "payment_receipt", "receipt_preview", "created_at"]

    def receipt_preview(self, obj):
        """Display receipt preview in inline"""
        if obj.payment_receipt:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" width="100" height="100" style="object-fit: cover;" /></a>',
                obj.payment_receipt.url,
                obj.payment_receipt.url
            )
        return "-"
    receipt_preview.short_description = _("Receipt Preview")


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
    list_display = ["id", "order", "amount", "status", "gateway", "latest_receipt_preview", "created_at"]
    list_filter = ["status", "gateway", "created_at"]
    search_fields = ["order__id", "reference_id", "transaction_id"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [PaymentTransactionInline]
    actions = ["verify_manual_payments", "reject_manual_payments"]

    fieldsets = (
        (None, {"fields": ("order", "amount", "status", "currency")}),
        (
            _("Payment Details"),
            {"fields": ("gateway", "reference_id", "transaction_id")},
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def latest_receipt_preview(self, obj):
        """Display preview of the latest transaction receipt in the list view"""
        latest_transaction = obj.transactions.filter(payment_receipt__isnull=False).first()
        if latest_transaction and latest_transaction.payment_receipt:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" width="50" height="50" style="object-fit: cover;" /></a>',
                latest_transaction.payment_receipt.url,
                latest_transaction.payment_receipt.url
            )
        return "-"
    latest_receipt_preview.short_description = _("Latest Receipt")

    def verify_manual_payments(self, request, queryset):
        """Verify manual payments and update order status"""
        verified_count = 0
        for payment in queryset:
            if payment.gateway == "MANUAL" and payment.status == PaymentStatus.PENDING:
                try:
                    # Update payment status
                    payment.status = PaymentStatus.COMPLETED
                    payment.save()

                    # Update order status
                    order = payment.order
                    if order.status == OrderStatus.AWAITING_VERIFICATION:
                        order.transition_to(OrderStatus.CONFIRMED)

                    verified_count += 1
                except ValidationError as e:
                    messages.error(
                        request,
                        f"Error verifying payment {payment.id}: {str(e)}"
                    )
            else:
                messages.warning(
                    request,
                    f"Payment {payment.id} is not a pending manual payment."
                )

        if verified_count > 0:
            messages.success(request, f"Successfully verified {verified_count} payment(s).")

    verify_manual_payments.short_description = _("Verify selected manual payments")

    def reject_manual_payments(self, request, queryset):
        """Reject manual payments and cancel orders"""
        rejected_count = 0
        for payment in queryset:
            if payment.gateway == "MANUAL" and payment.status == PaymentStatus.PENDING:
                try:
                    # Update payment status
                    payment.status = PaymentStatus.FAILED
                    payment.save()

                    # Update order status
                    order = payment.order
                    if order.status == OrderStatus.AWAITING_VERIFICATION:
                        order.transition_to(OrderStatus.CANCELLED)

                    rejected_count += 1
                except ValidationError as e:
                    messages.error(
                        request,
                        f"Error rejecting payment {payment.id}: {str(e)}"
                    )
            else:
                messages.warning(
                    request,
                    f"Payment {payment.id} is not a pending manual payment."
                )

        if rejected_count > 0:
            messages.success(request, f"Successfully rejected {rejected_count} payment(s).")

    reject_manual_payments.short_description = _("Reject selected manual payments")


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