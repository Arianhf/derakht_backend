# shop/serializers/cart.py

from rest_framework import serializers
from ..models import Cart, CartItem, PromoCode
from .product import ProductSerializer, ProductMinimalSerializer


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)
    anonymous_cart_id = serializers.CharField(required=False, allow_null=True)
    quantity = serializers.IntegerField(default=1, min_value=1)
    price = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    total_price = serializers.DecimalField(
        max_digits=12, decimal_places=0, read_only=True
    )

    class Meta:
        model = CartItem
        fields = [
            "product",
            "product_id",
            "anonymous_cart_id",
            "quantity",
            "price",
            "total_price",
        ]


class CartItemDetailSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source="product.title")
    product_price = serializers.IntegerField(source="product.price")
    product_image = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = (
            "id",
            "product_id",
            "product_title",
            "product_price",
            "product_image",
            "quantity",
            "total_price",
        )

    def get_product_image(self, obj):
        if obj.product.primary_image:
            return obj.product.primary_image.url
        return None

    def get_total_price(self, obj):
        return obj.quantity * obj.product.price


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
    cart_id = serializers.CharField(allow_null=True)
    is_authenticated = serializers.BooleanField()
    items_count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=0)
    items = CartItemSerializer(many=True)
    applied_promo = PromoCodeAppliedSerializer(required=False, allow_null=True)
    shipping_cost = serializers.DecimalField(
        max_digits=12, decimal_places=0, required=False, default=0
    )


# Input validation serializers for cart operations
class AddCartItemSerializer(serializers.Serializer):
    """Serializer for validating add item to cart requests"""

    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    anonymous_cart_id = serializers.UUIDField(required=False, allow_null=True)


class UpdateCartItemSerializer(serializers.Serializer):
    """Serializer for validating update cart item quantity requests"""

    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=0)
    anonymous_cart_id = serializers.UUIDField(required=False, allow_null=True)


class RemoveCartItemSerializer(serializers.Serializer):
    """Serializer for validating remove item from cart requests"""

    product_id = serializers.UUIDField()
    anonymous_cart_id = serializers.UUIDField(required=False, allow_null=True)
