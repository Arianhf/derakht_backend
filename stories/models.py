import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def validate_hex_color(value):
    """Validate that the value is a valid hex color code"""
    if not value:
        return
    hex_color_regex = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
    if not re.match(hex_color_regex, value):
        raise ValidationError(
            f'{value} is not a valid hex color code. Use format #RRGGBB or #RGB'
        )


class ActivityType(models.TextChoices):
    WRITE_FOR_DRAWING = "WRITE_FOR_DRAWING", "Write for Drawing"
    ILLUSTRATE = "ILLUSTRATE", "Illustrate Story"
    COMPLETE_STORY = "COMPLETE_STORY", "Complete Story"


class StoryStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    COMPLETED = "COMPLETED", "Completed"


# stories/models.py


class StoryTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    activity_type = models.CharField(max_length=20, choices=ActivityType.choices)
    cover_image = models.ImageField(
        upload_to="story_templates/covers/", null=True, blank=True
    )


class Story(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stories"
    )
    created_date = models.DateTimeField(auto_now_add=True)
    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices,
        default=ActivityType.WRITE_FOR_DRAWING,
    )
    status = models.CharField(
        max_length=20,
        choices=StoryStatus.choices,
        default=StoryStatus.DRAFT,
    )
    story_template = models.ForeignKey(
        StoryTemplate,
        on_delete=models.PROTECT,
        related_name="stories",
        null=True,
        blank=True,
    )
    cover_image = models.ImageField(upload_to="stories/covers/", null=True, blank=True)
    background_color = models.CharField(
        max_length=7,
        null=True,
        blank=True,
        validators=[validate_hex_color],
        help_text="Hex color code (e.g., #FF5733 or #FFF)",
    )
    font_color = models.CharField(
        max_length=7,
        null=True,
        blank=True,
        validators=[validate_hex_color],
        help_text="Hex color code for text (e.g., #000000 or #000)",
    )

    class Meta:
        ordering = ["-created_date"]


class StoryPartTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        StoryTemplate, related_name="template_parts", on_delete=models.CASCADE
    )
    position = models.IntegerField()
    prompt_text = models.TextField()
    illustration = models.ImageField(
        upload_to="template_illustrations/", null=True, blank=True
    )

    class Meta:
        ordering = ["position"]
        unique_together = ["template", "position"]


class StoryPart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, related_name="parts", on_delete=models.CASCADE)
    position = models.IntegerField()
    text = models.TextField()
    illustration = models.ImageField(upload_to="illustrations/", null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    story_part_template = models.ForeignKey(
        StoryPartTemplate,
        on_delete=models.PROTECT,
        related_name="stories",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["position"]
        unique_together = ["story", "position"]


class StoryCollection(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    stories = models.ManyToManyField(StoryTemplate)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ImageAsset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ImageField(upload_to="image_assets/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="image_assets"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
