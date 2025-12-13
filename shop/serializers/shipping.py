# shop/serializers/shipping.py

from rest_framework import serializers


class ShippingEstimateRequestSerializer(serializers.Serializer):
    province = serializers.CharField(required=True)
    city = serializers.CharField(required=True)
    cart_id = serializers.UUIDField(required=False, allow_null=True)


class ShippingMethodSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    cost = serializers.IntegerField()
    original_cost = serializers.IntegerField()
    is_free = serializers.BooleanField()
    estimated_delivery_days_min = serializers.IntegerField(required=False)
    estimated_delivery_days_max = serializers.IntegerField(required=False)
    estimated_delivery_hours_min = serializers.IntegerField(required=False)
    estimated_delivery_hours_max = serializers.IntegerField(required=False)
    is_available = serializers.BooleanField()
    available_for_provinces = serializers.ListField(
        child=serializers.CharField(), required=False
    )


class ShippingEstimateResponseSerializer(serializers.Serializer):
    shipping_methods = ShippingMethodSerializer(many=True)
    cart_total = serializers.IntegerField()
    free_shipping_threshold = serializers.IntegerField()
    message = serializers.CharField()
