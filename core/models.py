# core/models.py
import uuid
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


class FeatureFlag(models.Model):
    """Feature flag to control feature availability"""
    name = models.CharField(max_length=100, unique=True)
    enabled = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Feature Flag"
        verbose_name_plural = "Feature Flags"

    def __str__(self):
        return f"{self.name} ({'Enabled' if self.enabled else 'Disabled'})"


class Comment(models.Model):
    """
    Generic comment model that can be attached to any model (Product, BlogPost, etc.)
    Uses Django's ContentTypes framework for flexibility.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Generic foreign key to allow comments on any model
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Content Type"),
    )
    object_id = models.UUIDField(_("Object ID"))
    content_object = GenericForeignKey('content_type', 'object_id')

    # User information
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="comments",
        verbose_name=_("User"),
        null=True,
        blank=True,
    )
    user_name = models.CharField(
        _("User Name"),
        max_length=255,
        help_text=_("Display name or 'کاربر ناشناس' for anonymous users"),
    )

    # Comment content
    text = models.TextField(_("Comment Text"))

    # Moderation fields
    is_approved = models.BooleanField(_("Is Approved"), default=False)
    is_deleted = models.BooleanField(_("Is Deleted"), default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Comment")
        verbose_name_plural = _("Comments")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id", "-created_at"]),
            models.Index(fields=["user"]),
            models.Index(fields=["is_approved", "is_deleted"]),
        ]

    def __str__(self):
        return f"Comment by {self.user_name} on {self.content_object}"

    def save(self, *args, **kwargs):
        # Set user_name if not provided
        if not self.user_name:
            if self.user:
                # Use user's full name or email
                if self.user.first_name and self.user.last_name:
                    self.user_name = f"{self.user.first_name} {self.user.last_name}"
                else:
                    self.user_name = self.user.email.split("@")[0]
            else:
                self.user_name = "کاربر ناشناس"
        super().save(*args, **kwargs)