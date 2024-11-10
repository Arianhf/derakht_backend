from rest_framework import serializers
from .models import Story, StoryTemplate, StoryPart, StoryPartTemplate, StoryCollection


class StoryPartSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoryPart
        fields = ['id', 'position', 'text', 'illustration', 'created_date']


class StorySerializer(serializers.ModelSerializer):
    parts = StoryPartSerializer(many=True, read_only=True)

    class Meta:
        model = Story
        fields = ['id', 'title', 'author', 'created_date', 'activity_type', 'parts']


class StoryPartTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoryPartTemplate
        fields = ['id', 'position', 'prompt_text', 'illustration']


class StoryTemplateSerializer(serializers.ModelSerializer):
    template_parts = StoryPartTemplateSerializer(many=True, read_only=True)

    class Meta:
        model = StoryTemplate
        fields = ['id', 'title', 'description', 'activity_type', 'template_parts']


class StoryCollectionSerializer(serializers.ModelSerializer):
    stories = StoryTemplateSerializer(many=True, read_only=True)

    class Meta:
        model = StoryCollection
        fields = ['id', 'title', 'description', 'stories', 'created_at', 'updated_at']

    def create(self, validated_data):
        stories_data = self.context['request'].data.get('stories', [])
        collection = StoryCollection.objects.create(**validated_data)
        collection.stories.set(stories_data)
        return collection