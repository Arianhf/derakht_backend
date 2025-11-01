from rest_framework import serializers

from .models import (
    Story,
    StoryTemplate,
    StoryPart,
    StoryPartTemplate,
    StoryCollection,
    ImageAsset,
)


class ImageAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageAsset
        fields = ["id", "file", "created_at"]
        read_only_fields = ["id", "created_at"]


class StoryPartSerializer(serializers.ModelSerializer):
    illustration = serializers.SerializerMethodField()

    class Meta:
        model = StoryPart
        fields = [
            "id",
            "position",
            "text",
            "illustration",
            "created_date",
            "story_part_template",
        ]
        read_only_fields = ["position", "illustration"]

    def get_illustration(self, obj):
        if obj.illustration:
            return obj.illustration.url
        return None


class StoryPartTemplateSerializer(serializers.ModelSerializer):
    illustration = serializers.SerializerMethodField()

    class Meta:
        model = StoryPartTemplate
        fields = ["id", "position", "prompt_text", "illustration"]

    def get_illustration(self, obj):
        if obj.illustration:
            return obj.illustration.url
        return None


class StoryTemplateSerializer(serializers.ModelSerializer):
    template_parts = StoryPartTemplateSerializer(many=True, read_only=True)
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = StoryTemplate
        fields = [
            "id",
            "title",
            "description",
            "activity_type",
            "template_parts",
            "cover_image",
        ]

    def get_cover_image(self, obj):
        if obj.cover_image:
            return obj.cover_image.url
        return None


class StorySerializer(serializers.ModelSerializer):
    parts = StoryPartSerializer(many=True, read_only=True)
    author = serializers.PrimaryKeyRelatedField(read_only=True)
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = [
            "id",
            "title",
            "author",
            "created_date",
            "activity_type",
            "story_template",
            "parts",
            "cover_image",
            "background_color",
            "font_color",
        ]
        read_only_fields = ["author", "activity_type", "story_template"]

    def get_cover_image(self, obj):
        if obj.cover_image:
            return obj.cover_image.url
        return None


class StoryCollectionSerializer(serializers.ModelSerializer):
    stories = StoryTemplateSerializer(many=True, read_only=True)

    class Meta:
        model = StoryCollection
        fields = ["id", "title", "description", "stories", "created_at", "updated_at"]
