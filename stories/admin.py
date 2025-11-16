# admin.py
from django import forms
from django.contrib import admin

from .models import Story, StoryTemplate, StoryPart, StoryPartTemplate, StoryCollection


class StoryPartTemplateInlineForm(forms.ModelForm):
    class Meta:
        model = StoryPartTemplate
        fields = "__all__"

    def clean_prompt_text(self):
        prompt_text = self.cleaned_data.get("prompt_text")
        # Get the parent template's activity type if available
        template = self.cleaned_data.get("template") or (
            self.instance.template if self.instance and self.instance.pk else None
        )

        # For ILLUSTRATE mode, prompt text must not be empty
        if template and template.activity_type == "ILLUSTRATE":
            if not prompt_text or not prompt_text.strip():
                raise forms.ValidationError(
                    "Prompt text is required for ILLUSTRATE mode templates."
                )

        return prompt_text


class StoryPartTemplateInline(admin.TabularInline):
    model = StoryPartTemplate
    form = StoryPartTemplateInlineForm
    extra = 1
    ordering = ["position"]
    fields = ["position", "prompt_text", "illustration"]


class StoryTemplateAdminForm(forms.ModelForm):
    collections = forms.ModelMultipleChoiceField(
        queryset=StoryCollection.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select collections this template should belong to",
    )

    class Meta:
        model = StoryTemplate
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["collections"].initial = StoryCollection.objects.filter(
                stories=self.instance
            )

    def clean(self):
        cleaned_data = super().clean()
        activity_type = cleaned_data.get("activity_type")

        # For ILLUSTRATE mode, ensure all template parts will have prompt text
        # Note: This validation will run after the template is saved (when inline formsets are saved)
        # So we add a note to the activity_type help text instead
        if activity_type == "ILLUSTRATE" and self.instance.pk:
            # Check existing template parts
            empty_parts = self.instance.template_parts.filter(
                prompt_text__isnull=True
            ) | self.instance.template_parts.filter(prompt_text="")
            if empty_parts.exists():
                positions = [str(p.position) for p in empty_parts]
                raise forms.ValidationError(
                    f"ILLUSTRATE mode requires all story parts to have text. "
                    f"Parts at positions {', '.join(positions)} have no prompt text."
                )

        return cleaned_data

    def save(self, commit=True):
        template = super().save(commit=commit)
        if commit:
            # Get selected collections
            collections = self.cleaned_data.get("collections", [])

            # Remove template from collections that weren't selected
            for collection in StoryCollection.objects.filter(stories=template):
                if collection not in collections:
                    collection.stories.remove(template)

            # Add template to selected collections
            for collection in collections:
                collection.stories.add(template)

        return template


@admin.register(StoryTemplate)
class StoryTemplateAdmin(admin.ModelAdmin):
    form = StoryTemplateAdminForm
    inlines = [StoryPartTemplateInline]
    list_display = ["title", "activity_type", "get_collections", "has_cover_image"]
    list_filter = ["activity_type"]
    search_fields = ["title", "description"]

    fieldsets = (
        (
            None,
            {
                "fields": ("title", "description", "activity_type", "cover_image"),
            },
        ),
    )

    def get_collections(self, obj):
        return ", ".join([c.title for c in StoryCollection.objects.filter(stories=obj)])

    get_collections.short_description = "Collections"

    def has_cover_image(self, obj):
        return bool(obj.cover_image)

    has_cover_image.boolean = True
    has_cover_image.short_description = "Has Cover Image"


class StoryPartInline(admin.TabularInline):
    model = StoryPart
    extra = 1
    ordering = ["position"]


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "author",
        "activity_type",
        "created_date",
        "has_cover_image",
        "background_color",
        "font_color",
    ]
    list_filter = ["activity_type", "created_date"]
    search_fields = ["title", "author"]
    inlines = [StoryPartInline]
    readonly_fields = ["created_date"]
    fields = [
        "title",
        "author",
        "activity_type",
        "story_template",
        "cover_image",
        "background_color",
        "font_color",
        "created_date",
    ]

    def has_cover_image(self, obj):
        return bool(obj.cover_image)

    has_cover_image.boolean = True
    has_cover_image.short_description = "Has Cover Image"


@admin.register(StoryCollection)
class StoryCollectionAdmin(admin.ModelAdmin):
    list_display = ["title", "created_at", "updated_at", "get_story_count"]
    search_fields = ["title", "description"]
    filter_horizontal = ["stories"]

    def get_story_count(self, obj):
        return obj.stories.count()

    get_story_count.short_description = "Number of Stories"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("stories")


@admin.register(StoryPart)
class StoryPartAdmin(admin.ModelAdmin):
    list_display = ["story", "position", "created_date"]
    list_filter = ["created_date"]
    search_fields = ["text", "story__title"]
    ordering = ["story", "position"]


@admin.register(StoryPartTemplate)
class StoryPartTemplateAdmin(admin.ModelAdmin):
    list_display = ["template", "position"]
    list_filter = ["template"]
    search_fields = ["prompt_text", "template__title"]
    ordering = ["template", "position"]
