# core/serializers.py
from rest_framework import serializers
from .models import FeatureFlag

class FeatureFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureFlag
        fields = ['name', 'enabled', 'description']