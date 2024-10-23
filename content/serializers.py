from rest_framework import serializers
from .models import Story, StoryCollection

class StorySerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()

    class Meta:
        model = Story
        fields = ['id', 'title', 'content', 'author', 'created_at', 'updated_at']

class StoryCollectionSerializer(serializers.ModelSerializer):
    stories = StorySerializer(many=True, read_only=True)

    class Meta:
        model = StoryCollection
        fields = ['id', 'title', 'description', 'stories', 'created_at', 'updated_at']