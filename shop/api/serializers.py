from rest_framework import serializers

from ..models import Order, OrderItem, Payment, ProductImage, Product
from ..models.order import OrderStatusHistory


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "image", "image_url", "alt_text", "is_feature"]

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.get_rendition("original").url
        return None


class ProductListSerializer(serializers.ModelSerializer):
    feature_image = serializers.SerializerMethodField()
    age_range = serializers.CharField(source="age_range_display", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "price",
            "price_in_toman",
            "is_available",
            "feature_image",
            "min_age",
            "max_age",
            "age_range",
            "slug",
        ]

    def get_feature_image(self, obj):
        feature_image = obj.feature_image
        if feature_image and feature_image.image:
            return feature_image.image.get_rendition("original").url
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    age_range = serializers.CharField(source="age_range_display", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "description",
            "price",
            "price_in_toman",
            "stock",
            "sku",
            "is_available",
            "images",
            "min_age",
            "max_age",
            "age_range",
            "slug",
            "meta_title",
            "meta_description",
        ]


class ProductSerializer(serializers.ModelSerializer):
    feature_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "description",
            "price",
            "stock",
            "sku",
            "is_available",
            "slug",
            "price_in_toman",
            "feature_image",
        ]

    def get_feature_image(self, obj):
        feature_image = obj.feature_image
        if feature_image and feature_image.image:
            return feature_image.image.get_rendition("original").url
        return None


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "price", "total_price"]
        read_only_fields = ["price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "total_amount",
            "currency",
            "shipping_address",
            "phone_number",
            "items",
            "created_at",
        ]
        read_only_fields = ["status", "total_amount"]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "amount",
            "status",
            "payment_type",
            "provider",
            "reference_id",
            "created_at",
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
