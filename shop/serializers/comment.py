# shop/serializers/comment.py
from rest_framework import serializers
from ..models import ProductComment


class ProductCommentSerializer(serializers.ModelSerializer):
    """
    Serializer for listing product comments
    """
    class Meta:
        model = ProductComment
        fields = [
            "id",
            "product_id",
            "user_id",
            "user_name",
            "text",
            "created_at",
            "updated_at",
            "is_approved",
        ]
        read_only_fields = [
            "id",
            "product_id",
            "user_id",
            "user_name",
            "created_at",
            "updated_at",
            "is_approved",
        ]


class CreateProductCommentSerializer(serializers.Serializer):
    """
    Serializer for creating product comments
    """
    text = serializers.CharField(
        required=True,
        min_length=10,
        max_length=1000,
        error_messages={
            "required": "Comment text is required",
            "min_length": "Comment text is too short",
            "max_length": "Comment text is too long",
        }
    )

    def validate_text(self, value):
        """
        Validate the comment text
        """
        if len(value.strip()) < 10:
            raise serializers.ValidationError({
                "code": "COMMENT_TOO_SHORT",
                "message": "Comment text is too short",
                "severity": "error",
                "details": {
                    "field": "text",
                    "limit": 10
                }
            })

        if len(value) > 1000:
            raise serializers.ValidationError({
                "code": "COMMENT_TOO_LONG",
                "message": "Comment text is too long",
                "severity": "error",
                "details": {
                    "field": "text",
                    "limit": 1000
                }
            })

        return value.strip()
