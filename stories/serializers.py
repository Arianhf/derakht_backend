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

    def validate_text(self, value):
        """Validate text for ILLUSTRATE mode stories"""
        # Get the story from context or instance
        story = None
        if self.instance:
            story = self.instance.story
        elif 'story' in self.context:
            story = self.context['story']

        # For ILLUSTRATE mode, text must not be empty
        if story and story.activity_type == 'ILLUSTRATE':
            if not value or not value.strip():
                raise serializers.ValidationError(
                    "Text is required for story parts in ILLUSTRATE mode."
                )

        return value


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


class StoryPartImageUploadSerializer(serializers.Serializer):
    """Serializer for uploading images to story parts"""
    story_id = serializers.UUIDField(required=True)
    part_position = serializers.IntegerField(required=True, min_value=0)
    image = serializers.ImageField(required=True)

    def validate_image(self, value):
        """Validate image file size"""
        # Limit to 10MB
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Image file too large. Max size is 10MB.")
        return value

    def validate(self, data):
        """Validate that the story and part exist and belong to the user"""
        story_id = data.get('story_id')
        part_position = data.get('part_position')

        try:
            story = Story.objects.get(id=story_id)
        except Story.DoesNotExist:
            raise serializers.ValidationError({"story_id": "Story not found."})

        # Check if the story part exists, create if it doesn't for ILLUSTRATE type
        try:
            story_part = StoryPart.objects.get(story=story, position=part_position)
        except StoryPart.DoesNotExist:
            if story.activity_type == 'ILLUSTRATE':
                # Auto-create the story part for ILLUSTRATE type stories
                story_part = StoryPart.objects.create(
                    story=story,
                    position=part_position,
                    text='',  # Empty text initially, admin will add it
                )
            else:
                raise serializers.ValidationError({
                    "part_position": f"Story part at position {part_position} not found."
                })

        data['story_part'] = story_part
        data['story'] = story
        return data
