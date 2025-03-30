from rest_framework import serializers

from ..models import Order, OrderItem, ProductImage, Product, Category
from ..models.order import OrderStatusHistory


class CategorySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "parent", "image_url"]

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None


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
    age_range = serializers.CharField(source="age_range", read_only=True)

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
    age_range = serializers.CharField(source="age_range", read_only=True)

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
    price_in_toman = serializers.IntegerField(read_only=True)
    age_range = serializers.CharField(read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.UUIDField(
        write_only=True, required=False, allow_null=True
    )
    images = ProductImageSerializer(many=True, read_only=True)
    feature_image = serializers.SerializerMethodField()

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
            "slug",
            "meta_title",
            "meta_description",
            "min_age",
            "max_age",
            "age_range",
            "category_id",
            "category",
            "images",
            "feature_image",
            "created_at",
            "updated_at",
        ]

    def get_feature_image(self, obj):
        return obj.feature_image


class ProductMinimalSerializer(serializers.ModelSerializer):
    price_in_toman = serializers.IntegerField(read_only=True)
    feature_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "title", "price", "price_in_toman", "feature_image"]

    def get_feature_image(self, obj):
        return obj.feature_image
