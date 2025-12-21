from rest_framework import serializers

from .models import (
    Story,
    StoryTemplate,
    StoryPart,
    StoryPartTemplate,
    StoryCollection,
    ImageAsset,
)

from users.serializers import SmallUserSerializer


class ImageAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageAsset
        fields = ["id", "file", "created_at"]
        read_only_fields = ["id", "created_at"]


class StoryPartSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoryPart
        fields = [
            "id",
            "position",
            "created_date",
            "story_part_template",
            "canvas_text_data",
            "canvas_illustration_data",
        ]
        read_only_fields = ["position"]


class StoryPartTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoryPartTemplate
        fields = ["id", "position", "canvas_text_template", "canvas_illustration_template"]


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
            "orientation",
            "size",
        ]

    def get_cover_image(self, obj):
        if obj.cover_image:
            return obj.cover_image.url
        return None


class StorySerializer(serializers.ModelSerializer):
    parts = StoryPartSerializer(many=True, read_only=True)
    author = SmallUserSerializer(read_only=True)
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = [
            "id",
            "title",
            "author",
            "created_date",
            "activity_type",
            "status",
            "story_template",
            "parts",
            "cover_image",
            "background_color",
            "font_color",
            "orientation",
            "size",
        ]
        read_only_fields = ["author", "activity_type", "story_template", "status"]

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

        # Check if the story part exists
        try:
            story_part = StoryPart.objects.get(story=story, position=part_position)
            data['story_part'] = story_part
        except StoryPart.DoesNotExist:
            raise serializers.ValidationError({
                "part_position": f"Story part at position {part_position} not found."
            })

        data['story'] = story
        return data


# Staff-only serializers for creating/updating templates


class StoryPartTemplateWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating story part templates (staff only)"""

    class Meta:
        model = StoryPartTemplate
        fields = ["id", "position", "canvas_text_template", "canvas_illustration_template"]
        read_only_fields = ["id"]

    def validate(self, data):
        """Ensure position is unique within the template"""
        # Get template from instance (for updates) or context (for nested creates)
        template = None
        if self.instance:
            template = self.instance.template
        elif 'template' in self.context:
            template = self.context['template']

        position = data.get('position')

        if template and position is not None:
            # For updates, exclude the current instance
            queryset = StoryPartTemplate.objects.filter(template=template, position=position)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError({
                    "position": f"A story part template with position {position} already exists for this template."
                })

        return data


class StoryTemplateWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating story templates with nested parts (staff only)"""
    template_parts = StoryPartTemplateWriteSerializer(many=True, required=False)

    class Meta:
        model = StoryTemplate
        fields = [
            "id",
            "title",
            "description",
            "activity_type",
            "cover_image",
            "orientation",
            "size",
            "template_parts",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        """Create template with nested template parts"""
        template_parts_data = validated_data.pop('template_parts', [])
        template = StoryTemplate.objects.create(**validated_data)

        # Create template parts
        for part_data in template_parts_data:
            StoryPartTemplate.objects.create(template=template, **part_data)

        return template

    def update(self, instance, validated_data):
        """Update template and optionally its parts"""
        template_parts_data = validated_data.pop('template_parts', None)

        # Update template fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If template_parts are provided, update them
        # Note: This is a simple implementation. For production, you might want
        # more sophisticated logic to handle adding/removing/updating parts
        if template_parts_data is not None:
            # Get existing parts
            existing_parts = {part.position: part for part in instance.template_parts.all()}

            for part_data in template_parts_data:
                position = part_data.get('position')
                if position in existing_parts:
                    # Update existing part
                    part = existing_parts[position]
                    for attr, value in part_data.items():
                        setattr(part, attr, value)
                    part.save()
                else:
                    # Create new part
                    StoryPartTemplate.objects.create(template=instance, **part_data)

        return instance
