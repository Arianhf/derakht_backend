# shop/serializers/payment.py

from rest_framework import serializers
from ..models import Payment, PaymentTransaction


class PaymentReceiptUploadSerializer(serializers.Serializer):
    """Serializer for uploading payment receipt"""

    order_id = serializers.UUIDField(required=True)
    payment_receipt = serializers.ImageField(required=True)

    def validate_payment_receipt(self, value):
        """Validate the uploaded file is an image"""
        if value.size > 5 * 1024 * 1024:  # 5MB limit
            raise serializers.ValidationError("Image file too large. Max size is 5MB.")
        return value


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model"""

    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "amount",
            "status",
            "gateway",
            "currency",
            "reference_id",
            "transaction_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Serializer for PaymentTransaction model"""

    class Meta:
        model = PaymentTransaction
        fields = [
            "id",
            "payment",
            "amount",
            "transaction_id",
            "provider_status",
            "payment_receipt",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]
