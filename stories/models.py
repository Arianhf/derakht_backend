import uuid

from django.conf import settings
from django.db import models


class ActivityType(models.TextChoices):
    WRITE_FOR_DRAWING = 'WRITE_FOR_DRAWING', 'Write for Drawing'
    ILLUSTRATE = 'ILLUSTRATE', 'Illustrate Story'
    COMPLETE_STORY = 'COMPLETE_STORY', 'Complete Story'


class StoryTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices
    )


class Story(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stories'
    )
    created_date = models.DateTimeField(auto_now_add=True)
    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices,
        default=ActivityType.WRITE_FOR_DRAWING
    )
    story_template = models.ForeignKey(
        StoryTemplate,
        on_delete=models.PROTECT,
        related_name='stories',
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['-created_date']


class StoryPartTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(StoryTemplate, related_name='template_parts', on_delete=models.CASCADE)
    position = models.IntegerField()
    prompt_text = models.TextField()
    illustration = models.ImageField(upload_to='template_illustrations/', null=True, blank=True)

    class Meta:
        ordering = ['position']
        unique_together = ['template', 'position']


class StoryPart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, related_name='parts', on_delete=models.CASCADE)
    position = models.IntegerField()
    text = models.TextField()
    illustration = models.ImageField(upload_to='illustrations/', null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    story_part_template = models.ForeignKey(
        StoryPartTemplate,
        on_delete=models.PROTECT,
        related_name='stories',
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['position']
        unique_together = ['story', 'position']


class StoryCollection(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    stories = models.ManyToManyField(StoryTemplate)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ImageAsset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ImageField(upload_to='image_assets/')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='image_assets'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
