from django.contrib import admin

from .models import FeatureFlag


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ('name', 'enabled', 'created_at', 'updated_at')
    list_filter = ('enabled', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('enabled',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('name', 'enabled', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )