# core/wagtail_hooks.py
from wagtail_modeladmin.options import ModelAdmin, modeladmin_register

from .models import FeatureFlag

class FeatureFlagAdmin(ModelAdmin):
    model = FeatureFlag
    menu_label = 'Feature Flags'
    menu_icon = 'cog'
    menu_order = 300
    add_to_settings_menu = True
    list_display = ('name', 'enabled', 'description', 'updated_at')
    list_filter = ('enabled',)
    search_fields = ('name', 'description')

modeladmin_register(FeatureFlagAdmin)