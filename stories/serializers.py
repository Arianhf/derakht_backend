from rest_framework import serializers
from .models import Story, StoryTemplate, StoryPart, StoryPartTemplate, StoryCollection, ImageAsset


class ImageAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageAsset
        fields = ['id', 'file', 'created_at']
        read_only_fields = ['id', 'created_at']


class StoryPartSerializer(serializers.ModelSerializer):
    illustration_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    illustration = serializers.SerializerMethodField()

    class Meta:
        model = StoryPart
        fields = ['id', 'position', 'text', 'illustration', 'illustration_id', 'created_date', 'story_part_template']
        read_only_fields = ['position', 'illustration']

    def get_illustration(self, obj):
        if obj.illustration:
            return obj.illustration.url
        return None

    def create(self, validated_data):
        illustration_id = validated_data.pop('illustration_id', None)
        if illustration_id:
            try:
                image_asset = ImageAsset.objects.get(
                    id=illustration_id,
                    uploaded_by=self.context['request'].user
                )
                validated_data['illustration'] = image_asset.file
            except ImageAsset.DoesNotExist:
                raise serializers.ValidationError({"illustration_id": "Invalid image ID"})

        return super().create(validated_data)

    def update(self, instance, validated_data):
        illustration_id = validated_data.pop('illustration_id', None)
        if illustration_id:
            try:
                image_asset = ImageAsset.objects.get(
                    id=illustration_id,
                    uploaded_by=self.context['request'].user
                )
                validated_data['illustration'] = image_asset.file
            except ImageAsset.DoesNotExist:
                raise serializers.ValidationError({"illustration_id": "Invalid image ID"})
        elif illustration_id is None and 'illustration_id' in self.initial_data:
            # If illustration_id is explicitly set to null, remove the illustration
            validated_data['illustration'] = None

        return super().update(instance, validated_data)


class StoryPartTemplateSerializer(serializers.ModelSerializer):
    illustration = serializers.SerializerMethodField()

    class Meta:
        model = StoryPartTemplate
        fields = ['id', 'position', 'prompt_text', 'illustration']

    def get_illustration(self, obj):
        if obj.illustration:
            return obj.illustration.url
        return None


class StoryTemplateSerializer(serializers.ModelSerializer):
    template_parts = StoryPartTemplateSerializer(many=True, read_only=True)

    class Meta:
        model = StoryTemplate
        fields = ['id', 'title', 'description', 'activity_type', 'template_parts']


class StorySerializer(serializers.ModelSerializer):
    parts = StoryPartSerializer(many=True, read_only=True)
    author = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Story
        fields = ['id', 'title', 'author', 'created_date', 'activity_type', 'story_template', 'parts']
        read_only_fields = ['author', 'activity_type', 'story_template']


class StoryCollectionSerializer(serializers.ModelSerializer):
    stories = StoryTemplateSerializer(many=True, read_only=True)

    class Meta:
        model = StoryCollection
        fields = ['id', 'title', 'description', 'stories', 'created_at', 'updated_at']