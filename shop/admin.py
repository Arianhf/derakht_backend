from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import (
    Product, ProductImage,
    Order, OrderItem,
    Payment, PaymentTransaction,
    Invoice, InvoiceItem
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'price', 'stock', 'is_available', 'created_at']
    list_filter = ['is_available', 'created_at']
    search_fields = ['title', 'description', 'sku']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'description', 'price', 'stock', 'sku')
        }),
        (_('Status'), {
            'fields': ('is_available', 'is_active')
        }),
        (_('SEO'), {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['price']
    raw_id_fields = ['product']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['id', 'user__email', 'phone_number']
    readonly_fields = ['created_at', 'updated_at', 'total_amount']
    inlines = [OrderItemInline]
    fieldsets = (
        (None, {
            'fields': ('user', 'status', 'currency', 'total_amount')
        }),
        (_('Contact Information'), {
            'fields': ('phone_number', 'shipping_address')
        }),
        (_('Additional Information'), {
            'fields': ('note', 'tracking_code'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['cancel_orders', 'mark_orders_shipped', 'mark_orders_delivered']

    def cancel_orders(self, request, queryset):
        for order in queryset:
            if order.can_cancel:
                try:
                    order.cancel()
                except ValidationError as e:
                    messages.error(request, f"Error cancelling order {order.id}: {str(e)}")
            else:
                messages.warning(
                    request,
                    f"Order {order.id} cannot be cancelled in its current state."
                )

    cancel_orders.short_description = _("Cancel selected orders")

    def mark_orders_shipped(self, request, queryset):
        # This is simplified - you might want to add a form for tracking codes
        for order in queryset:
            if order.can_ship:
                try:
                    order.confirm_shipping(f"TRACK-{order.id}")
                except ValidationError as e:
                    messages.error(request, f"Error shipping order {order.id}: {str(e)}")
            else:
                messages.warning(
                    request,
                    f"Order {order.id} cannot be marked as shipped in its current state."
                )

    mark_orders_shipped.short_description = _("Mark selected orders as shipped")

    def mark_orders_delivered(self, request, queryset):
        for order in queryset:
            if order.can_deliver:
                try:
                    order.mark_delivered()
                except ValidationError as e:
                    messages.error(request, f"Error marking order {order.id} as delivered: {str(e)}")
            else:
                messages.warning(
                    request,
                    f"Order {order.id} cannot be marked as delivered in its current state."
                )

    mark_orders_delivered.short_description = _("Mark selected orders as delivered")


class PaymentTransactionInline(admin.TabularInline):
    model = PaymentTransaction
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'amount', 'status', 'payment_type', 'created_at']
    list_filter = ['status', 'payment_type', 'provider', 'created_at']
    search_fields = ['order__id', 'reference_id']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PaymentTransactionInline]
    fieldsets = (
        (None, {
            'fields': ('order', 'amount', 'status', 'currency')
        }),
        (_('Payment Details'), {
            'fields': ('payment_type', 'provider', 'reference_id')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ['product_title', 'product_sku', 'quantity', 'price']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'order', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['invoice_number', 'order__id', 'phone_number']
    readonly_fields = ['invoice_number', 'created_at', 'updated_at']
    inlines = [InvoiceItemInline]
    fieldsets = (
        (None, {
            'fields': ('order', 'invoice_number', 'status', 'total_amount', 'currency')
        }),
        (_('Contact Information'), {
            'fields': ('phone_number', 'shipping_address')
        }),
        (_('Files'), {
            'fields': ('pdf_file',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
