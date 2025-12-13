from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

from .models import FeatureFlag, Comment


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


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "content_type",
        "content_object",
        "user_name",
        "text_preview",
        "is_approved",
        "is_deleted",
        "created_at",
    )
    list_filter = ("content_type", "is_approved", "is_deleted", "created_at")
    search_fields = ("text", "user_name", "user__email")
    readonly_fields = ("created_at", "updated_at", "content_type", "object_id")
    actions = ["approve_comments", "reject_comments", "delete_comments"]

    fieldsets = (
        (None, {"fields": ("content_type", "object_id", "user", "user_name", "text")}),
        (
            _("Status"),
            {"fields": ("is_approved", "is_deleted")},
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def text_preview(self, obj):
        """Show a preview of the comment text"""
        if len(obj.text) > 50:
            return obj.text[:50] + "..."
        return obj.text

    text_preview.short_description = _("Comment")

    def approve_comments(self, request, queryset):
        """Approve selected comments"""
        updated = queryset.update(is_approved=True)
        messages.success(request, f"Successfully approved {updated} comment(s).")

    approve_comments.short_description = _("Approve selected comments")

    def reject_comments(self, request, queryset):
        """Reject selected comments"""
        updated = queryset.update(is_approved=False)
        messages.success(request, f"Successfully rejected {updated} comment(s).")

    reject_comments.short_description = _("Reject selected comments")

    def delete_comments(self, request, queryset):
        """Soft delete selected comments"""
        updated = queryset.update(is_deleted=True)
        messages.success(request, f"Successfully deleted {updated} comment(s).")

    delete_comments.short_description = _("Delete selected comments")