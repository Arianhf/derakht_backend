# shop/serializers/cart.py

from rest_framework import serializers
from ..models import CartItem, PromoCode
from .product import ProductSerializer, ProductMinimalSerializer


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    total_price = serializers.DecimalField(
        max_digits=12, decimal_places=0, read_only=True
    )

    class Meta:
        model = CartItem
        fields = ["product", "product_id", "quantity", "price", "total_price"]


class CartItemMinimalSerializer(serializers.ModelSerializer):
    product = ProductMinimalSerializer(read_only=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    total_price = serializers.DecimalField(
        max_digits=12, decimal_places=0, read_only=True
    )

    class Meta:
        model = CartItem
        fields = ["product", "quantity", "price", "total_price"]


class PromoCodeAppliedSerializer(serializers.Serializer):
    code = serializers.CharField()
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=0)


class CartDetailsSerializer(serializers.Serializer):
    items_count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=0)
    items = CartItemSerializer(many=True)
    applied_promo = PromoCodeAppliedSerializer(required=False, allow_null=True)
    shipping_cost = serializers.DecimalField(
        max_digits=12, decimal_places=0, required=False, default=0
    )
