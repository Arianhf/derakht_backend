# core/utils.py
from django.core.cache import cache
from .models import FeatureFlag


def is_feature_enabled(name, default=False):
    """
    Check if a feature flag is enabled.
    Uses cache to avoid database queries.

    Args:
        name (str): The name of the feature flag
        default (bool): Default value if flag doesn't exist

    Returns:
        bool: Whether the feature is enabled
    """
    cache_key = f"feature_flag_{name}"
    flag_enabled = cache.get(cache_key)

    if flag_enabled is None:
        try:
            flag = FeatureFlag.objects.get(name=name)
            flag_enabled = flag.enabled
            # Cache for 5 minutes
            cache.set(cache_key, flag_enabled, 300)
        except FeatureFlag.DoesNotExist:
            # If flag doesn't exist, use default value
            flag_enabled = default
            cache.set(cache_key, flag_enabled, 300)

    return flag_enabled