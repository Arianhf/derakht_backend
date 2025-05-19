# core/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import FeatureFlag
from .serializers import FeatureFlagSerializer
from .utils import is_feature_enabled

@api_view(['GET'])
def feature_flags(request):
    """Get all feature flags"""
    flags = FeatureFlag.objects.all()
    serializer = FeatureFlagSerializer(flags, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def feature_flag_detail(request, name):
    """Get a specific feature flag by name"""
    enabled = is_feature_enabled(name)
    return Response({"name": name, "enabled": enabled})