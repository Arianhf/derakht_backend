# shop/serializers/order.py

from rest_framework import serializers
from ..models import (
    Order,
    OrderItem,
    ShippingInfo,
    PaymentInfo,
)
from .product import ProductMinimalSerializer, ProductSerializer
from ..models.order import OrderStatusHistory


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductMinimalSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "price", "total_price"]
        read_only_fields = ["price", "total_price"]


class ShippingInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingInfo
        fields = [
            "address",
            "city",
            "province",
            "postal_code",
            "recipient_name",
            "phone_number",
        ]


class PaymentInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentInfo
        fields = ["method", "transaction_id", "payment_date", "status"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_info = ShippingInfoSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "total_amount",
            "currency",
            "phone_number",
            "shipping_info",
            "items",
            "created_at",
        ]
        read_only_fields = ["status", "total_amount"]


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_info = ShippingInfoSerializer(read_only=True)
    payment_info = PaymentInfoSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "total_amount",
            "currency",
            "phone_number",
            "items",
            "created_at",
            "shipping_info",
            "payment_info",
        ]


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ["from_status", "to_status", "note", "created_at"]


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["product", "quantity", "price", "total_price"]

    def get_total_price(self, obj):
        if isinstance(obj, OrderItem):
            return obj.total_price
        else:
            return obj["price"] * obj["quantity"]


class CartDetailsSerializer(serializers.Serializer):
    items_count = serializers.IntegerField()
    product_count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=0)
    items = CartItemSerializer(many=True)
