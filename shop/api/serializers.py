from rest_framework import serializers

from ..models import Order, OrderItem, Payment, ProductImage, Product
from ..models.order import OrderStatusHistory


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'title', 'description', 'price', 'stock',
            'sku', 'is_available', 'slug', 'price_in_toman'
        ]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_feature']


class ProductDetailSerializer(ProductSerializer):
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta(ProductSerializer.Meta):
        fields = ProductSerializer.Meta.fields + ['images', 'meta_title', 'meta_description']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'price']
        read_only_fields = ['price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'total_amount', 'currency',
            'shipping_address', 'phone_number', 'items',
            'created_at'
        ]
        read_only_fields = ['status', 'total_amount']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'amount', 'status',
            'payment_type', 'provider', 'reference_id',
            'created_at'
        ]


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ['from_status', 'to_status', 'note', 'created_at']


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'price', 'total_price']


class CartDetailsSerializer(serializers.Serializer):
    items_count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=0)
    items = CartItemSerializer(many=True)
