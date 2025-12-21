# admin.py
from django import forms
from django.contrib import admin
from django.utils.html import format_html
import json

from .models import Story, StoryTemplate, StoryPart, StoryPartTemplate, StoryCollection


class StoryPartTemplateInline(admin.TabularInline):
    model = StoryPartTemplate
    extra = 1
    ordering = ["position"]
    fields = ["position", "canvas_text_template", "canvas_illustration_template"]

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Add custom widget for JSON fields with better formatting
        formset.form.base_fields['canvas_text_template'].widget = forms.Textarea(attrs={'rows': 4, 'cols': 60, 'placeholder': 'Enter JSON for text canvas template'})
        formset.form.base_fields['canvas_illustration_template'].widget = forms.Textarea(attrs={'rows': 4, 'cols': 60, 'placeholder': 'Enter JSON for illustration canvas template'})
        return formset


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
    list_display = ["title", "activity_type", "orientation", "size", "get_part_count", "get_collections", "has_cover_image"]
    list_filter = ["activity_type", "orientation", "size"]
    search_fields = ["title", "description"]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("title", "description", "activity_type"),
            },
        ),
        (
            "Display Settings",
            {
                "fields": ("cover_image", "orientation", "size"),
            },
        ),
        (
            "Collections",
            {
                "fields": ("collections",),
                "description": "Select which collections this template should belong to",
            },
        ),
    )

    def get_part_count(self, obj):
        return obj.template_parts.count()

    get_part_count.short_description = "# of Parts"

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
        "orientation",
        "size",
    ]
    list_filter = ["activity_type", "created_date", "orientation", "size"]
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
        "orientation",
        "size",
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
    list_display = ["story", "position", "created_date", "has_text_canvas", "has_illustration_canvas"]
    list_filter = ["created_date"]
    search_fields = ["story__title"]
    ordering = ["story", "position"]
    fields = ["story", "position", "story_part_template", "canvas_text_data", "canvas_illustration_data", "created_date"]
    readonly_fields = ["created_date"]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name in ['canvas_text_data', 'canvas_illustration_data']:
            formfield.widget = forms.Textarea(attrs={'rows': 10, 'cols': 80})
        return formfield

    def has_text_canvas(self, obj):
        return bool(obj.canvas_text_data)

    has_text_canvas.boolean = True
    has_text_canvas.short_description = "Has Text Canvas"

    def has_illustration_canvas(self, obj):
        return bool(obj.canvas_illustration_data)

    has_illustration_canvas.boolean = True
    has_illustration_canvas.short_description = "Has Illustration Canvas"


@admin.register(StoryPartTemplate)
class StoryPartTemplateAdmin(admin.ModelAdmin):
    list_display = ["template", "position", "has_text_canvas_template", "has_illustration_canvas_template"]
    list_filter = ["template"]
    search_fields = ["template__title"]
    ordering = ["template", "position"]
    fields = ["template", "position", "canvas_text_template", "canvas_illustration_template"]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name in ['canvas_text_template', 'canvas_illustration_template']:
            formfield.widget = forms.Textarea(attrs={'rows': 10, 'cols': 80})
        return formfield

    def has_text_canvas_template(self, obj):
        return bool(obj.canvas_text_template)

    has_text_canvas_template.boolean = True
    has_text_canvas_template.short_description = "Has Text Canvas"

    def has_illustration_canvas_template(self, obj):
        return bool(obj.canvas_illustration_template)

    has_illustration_canvas_template.boolean = True
    has_illustration_canvas_template.short_description = "Has Illustration Canvas"
