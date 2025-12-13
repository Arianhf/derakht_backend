# core/serializers.py
from rest_framework import serializers
from .models import FeatureFlag, Comment


class FeatureFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureFlag
        fields = ['name', 'enabled', 'description']


class CommentSerializer(serializers.ModelSerializer):
    """
    Serializer for listing comments
    """
    content_type_name = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "content_type",
            "content_type_name",
            "object_id",
            "user_id",
            "user_name",
            "text",
            "created_at",
            "updated_at",
            "is_approved",
        ]
        read_only_fields = [
            "id",
            "content_type",
            "content_type_name",
            "object_id",
            "user_id",
            "user_name",
            "created_at",
            "updated_at",
            "is_approved",
        ]

    def get_content_type_name(self, obj):
        """Return human-readable content type name"""
        return obj.content_type.model


class CreateCommentSerializer(serializers.Serializer):
    """
    Serializer for creating comments
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