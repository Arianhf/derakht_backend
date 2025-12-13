"""
Factory Boy factories for stories app models.
"""

import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
import uuid

from stories.models import (
    StoryTemplate,
    StoryPartTemplate,
    Story,
    StoryPart,
    StoryCollection,
    ImageAsset,
)

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """User factory for stories tests."""

    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Faker("name")
    phone_number = "+989123456789"
    age = factory.Faker("random_int", min=5, max=15)
    is_active = True

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        if create:
            obj.set_password(extracted or "testpass123")
            obj.save()


# ============================================================================
# STORY TEMPLATE FACTORIES
# ============================================================================


class StoryTemplateFactory(DjangoModelFactory):
    """Factory for creating StoryTemplate instances."""

    class Meta:
        model = StoryTemplate

    title = factory.Faker("sentence", nb_words=4)
    description = factory.Faker("paragraph")
    activity_type = "COMPLETE_STORY"
    orientation = "PORTRAIT"
    size = "A4"
    is_active = True

    @factory.post_generation
    def parts(obj, create, extracted, **kwargs):
        """
        Create template parts.
        Usage: StoryTemplateFactory(parts=5)
        """
        if create and extracted:
            count = extracted if isinstance(extracted, int) else 3
            for i in range(count):
                StoryPartTemplateFactory(template=obj, position=i)


class StoryPartTemplateFactory(DjangoModelFactory):
    """Factory for creating StoryPartTemplate instances."""

    class Meta:
        model = StoryPartTemplate

    template = factory.SubFactory(StoryTemplateFactory)
    position = factory.Sequence(lambda n: n)
    prompt = factory.Faker("sentence", nb_words=8)
    # Note: illustration field (Wagtail image) would need more complex setup


# ============================================================================
# STORY FACTORIES
# ============================================================================


class StoryFactory(DjangoModelFactory):
    """Factory for creating Story instances."""

    class Meta:
        model = Story

    user = factory.SubFactory(UserFactory)
    template = factory.SubFactory(StoryTemplateFactory)
    title = factory.Faker("sentence", nb_words=4)
    status = "DRAFT"
    background_color = "#FFFFFF"
    font_color = "#000000"
    is_active = True

    @factory.post_generation
    def parts(obj, create, extracted, **kwargs):
        """
        Create story parts.
        Usage: StoryFactory(parts=3)
        """
        if create and extracted:
            count = extracted if isinstance(extracted, int) else 2
            for i in range(count):
                StoryPartFactory(story=obj, position=i)

    @factory.post_generation
    def completed(obj, create, extracted, **kwargs):
        """
        Mark story as completed.
        Usage: StoryFactory(completed=True)
        """
        if create and extracted:
            obj.status = "COMPLETED"
            obj.save()


class StoryPartFactory(DjangoModelFactory):
    """Factory for creating StoryPart instances."""

    class Meta:
        model = StoryPart

    story = factory.SubFactory(StoryFactory)
    position = factory.Sequence(lambda n: n)
    content = factory.Faker("paragraph")
    canvas_data = None  # JSON field - can be customized in tests
    is_active = True


# ============================================================================
# STORY COLLECTION FACTORY
# ============================================================================


class StoryCollectionFactory(DjangoModelFactory):
    """Factory for creating StoryCollection instances."""

    class Meta:
        model = StoryCollection

    name = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("paragraph")
    is_active = True

    @factory.post_generation
    def templates(obj, create, extracted, **kwargs):
        """
        Add templates to collection.
        Usage: StoryCollectionFactory(templates=3)
        """
        if create and extracted:
            count = extracted if isinstance(extracted, int) else 2
            for _ in range(count):
                template = StoryTemplateFactory()
                obj.templates.add(template)


# ============================================================================
# IMAGE ASSET FACTORY
# ============================================================================


class ImageAssetFactory(DjangoModelFactory):
    """Factory for creating ImageAsset instances."""

    class Meta:
        model = ImageAsset

    user = factory.SubFactory(UserFactory)
    # Note: image field would need actual file upload in tests
    # For most tests, we can skip this or use SimpleUploadedFile
    is_active = True


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def create_complete_story(user=None, part_count=3):
    """
    Helper to create a completed story with parts.

    Usage:
        story = create_complete_story(user=my_user, part_count=5)
    """
    if user is None:
        user = UserFactory()

    template = StoryTemplateFactory(parts=part_count)
    story = StoryFactory(user=user, template=template, status="COMPLETED")

    for i in range(part_count):
        StoryPartFactory(story=story, position=i)

    return story


def create_story_from_template(template=None, user=None):
    """
    Helper to create a story from a template (mimics the API behavior).

    Usage:
        template = StoryTemplateFactory(parts=3)
        story = create_story_from_template(template=template)
    """
    if template is None:
        template = StoryTemplateFactory(parts=3)

    if user is None:
        user = UserFactory()

    story = StoryFactory(
        user=user,
        template=template,
        title=template.title,
        status="DRAFT",
    )

    # Create story parts from template parts
    for template_part in template.template_parts.all():
        StoryPartFactory(
            story=story,
            position=template_part.position,
            content="",  # User will fill this in
        )

    return story


def create_collection_with_templates(template_count=3):
    """
    Helper to create a collection with multiple templates.

    Usage:
        collection = create_collection_with_templates(template_count=5)
    """
    collection = StoryCollectionFactory()

    for _ in range(template_count):
        template = StoryTemplateFactory()
        collection.templates.add(template)

    return collection
