import json

from django import forms
import jdatetime
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from rest_framework.fields import DateField
from taggit.models import TaggedItemBase
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.api import APIField
from wagtail.fields import RichTextField
from wagtail.models import Page, Orderable
from wagtail.search import index
from blog.panels import JalaliDatePanel, Select2FieldPanel
from blog.serializers import (
    CommaSeparatedListField,
    JalaliDateField,
    RichTextField as RichTextFieldSerializer,
)
from users.serializers import SmallUserSerializer


class BlogIndexPage(Page):
    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [FieldPanel("intro")]

    def get_context(self, request):
        context = super().get_context(request)
        blogposts = BlogPost.objects.child_of(self).live().order_by("-date")

        # Filter by tag
        tag = request.GET.get("tag")
        if tag:
            blogposts = blogposts.filter(tags__slug=tag)
            context["current_tag"] = tag

        # Filter by category
        category_slug = request.GET.get("category")
        if category_slug:
            try:
                category = BlogCategory.objects.get(slug=category_slug)
                blogposts = blogposts.filter(categories=category)
                context["current_category"] = category
            except BlogCategory.DoesNotExist:
                pass

        context["blogposts"] = blogposts

        # Add all categories to context
        context["categories"] = BlogCategory.objects.all()

        return context

    def get_tag_url(self, tag):
        return f"{self.url}?tag={tag.slug}"


class BlogPostTag(TaggedItemBase):
    content_object = ParentalKey(
        "BlogPost", related_name="tagged_items", on_delete=models.CASCADE
    )


class BlogPost(Page):
    date = models.DateField("Post date")
    subtitle = models.CharField(max_length=500, blank=True)
    intro = models.CharField(max_length=2000)
    alternative_titles = models.TextField(
        blank=True, help_text="Enter alternative titles separated by commas"
    )
    header_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    body = RichTextField(blank=True)
    tags = ClusterTaggableManager(through=BlogPostTag, blank=True)
    reading_time = models.PositiveIntegerField(default=0)
    featured = models.BooleanField(
        default=False,
    )
    hero = models.BooleanField(
        default=False, help_text="Only one blog post can be the hero at a time"
    )
    categories = ParentalManyToManyField(
        "BlogCategory", blank=True, related_name="blogposts"
    )
    related_posts = ParentalManyToManyField(
        "self", blank=True, symmetrical=False, related_name="posts_related_to"
    )

    # SEO Fields
    excerpt = models.TextField(
        blank=True,
        help_text="Short summary for post previews (150-200 characters)."
    )
    word_count = models.PositiveIntegerField(
        default=0,
        blank=True,
        help_text="Auto-calculated from body content"
    )
    canonical_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Canonical URL if content exists elsewhere"
    )
    og_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Custom Open Graph image for social media sharing. Falls back to header_image if not provided."
    )
    featured_snippet = models.TextField(
        blank=True,
        help_text="Optimized content for Google featured snippets (40-60 words)"
    )
    noindex = models.BooleanField(
        default=False,
        help_text="Prevent search engines from indexing this post"
    )

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("subtitle"),
        index.SearchField("body"),
        index.SearchField("alternative_titles"),
        index.RelatedFields(
            "categories",
            [
                index.SearchField("name"),
            ],
        ),
    ]

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                JalaliDatePanel("date"),
                FieldPanel("subtitle"),
                FieldPanel("alternative_titles"),
                FieldPanel("featured"),
                FieldPanel("hero"),
                FieldPanel("categories", widget=forms.CheckboxSelectMultiple),
                Select2FieldPanel(
                    "related_posts",
                    select2_options={
                        "placeholder": "Search for related posts...",
                        "multiple": True,
                    },
                ),
            ],
            heading="Post Information",
        ),
        FieldPanel("intro"),
        FieldPanel("excerpt"),
        FieldPanel("header_image"),
        FieldPanel("body"),
        FieldPanel("tags"),
        FieldPanel("reading_time"),
        MultiFieldPanel(
            [
                FieldPanel("canonical_url"),
                FieldPanel("og_image"),
                FieldPanel("featured_snippet"),
                FieldPanel("noindex"),
            ],
            heading="SEO Settings",
            classname="collapsible collapsed",
        ),
    ]

    api_fields = [
        APIField("date", serializer=DateField(format="%d %B %Y")),
        APIField("subtitle"),
        APIField("intro"),
        APIField("excerpt"),
        APIField("alternative_titles", serializer=CommaSeparatedListField()),
        APIField("header_image"),
        APIField("body", serializer=RichTextFieldSerializer()),
        APIField("tags"),
        APIField("jalali_date", serializer=JalaliDateField()),
        APIField("published_date"),
        APIField("updated_date"),
        APIField("reading_time"),
        APIField("word_count"),
        APIField("owner", serializer=SmallUserSerializer()),
        APIField("featured"),
        APIField("hero"),
        APIField("categories"),
        # SEO fields
        APIField("seo_title"),
        APIField("search_description"),
        APIField("canonical_url"),
        APIField("og_image"),
        APIField("featured_snippet"),
        APIField("noindex"),
    ]

    # Property to get Jalali date
    @property
    def jalali_date(self):
        if self.date:
            return jdatetime.date.fromgregorian(date=self.date)
        return None

    # Property to get published date in ISO 8601 format
    @property
    def published_date(self):
        if self.date:
            # Combine date with a default time (midnight) and return ISO format
            from datetime import datetime, time
            return datetime.combine(self.date, time.min).isoformat() + "Z"
        return None

    # Property to get updated date in ISO 8601 format
    @property
    def updated_date(self):
        if self.last_published_at:
            # Only return if post has been modified after initial publication
            if self.first_published_at and self.last_published_at > self.first_published_at:
                return self.last_published_at.isoformat().replace('+00:00', 'Z')
        return None

    def calculate_word_count(self):
        """Calculate word count from body content"""
        from wagtail.rich_text import expand_db_html
        from django.utils.html import strip_tags

        if self.body:
            # Convert rich text to HTML, then strip tags to get plain text
            html_content = expand_db_html(self.body)
            plain_text = strip_tags(html_content)
            # Count words
            words = plain_text.split()
            return len(words)
        return 0

    def save(self, *args, **kwargs):
        # Auto-calculate word count if body exists
        if self.body:
            self.word_count = self.calculate_word_count()
        super().save(*args, **kwargs)

    def get_alternative_titles_list(self):
        """Returns alternative titles as a list"""
        if self.alternative_titles:
            return [title.strip() for title in self.alternative_titles.split(",")]
        return []

    @property
    def get_alternative_titles(self):
        return self.get_alternative_titles_list()

    def get_schema_markup(self):
        """Generate schema.org JSON-LD markup"""
        schema = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": self.title,
            "alternativeHeadline": self.subtitle or "",
            "alternativeHeadlines": self.get_alternative_titles_list(),
            "description": self.intro,
            "author": {
                "@type": "Person",
                "name": self.owner.get_full_name() if self.owner else "Anonymous",
            },
            "datePublished": self.date.isoformat(),
            "dateModified": (
                self.last_published_at.isoformat()
                if self.last_published_at
                else self.date.isoformat()
            ),
            "mainEntityOfPage": {"@type": "WebPage", "@id": self.get_full_url()},
            "url": self.get_full_url(),
        }

        # Add image if exists
        if self.header_image:
            schema["image"] = {
                "@type": "ImageObject",
                "url": self.header_image.get_rendition("original").url,
                "width": self.header_image.width,
                "height": self.header_image.height,
            }

        # Add tags if they exist
        if self.tags.all():
            schema["keywords"] = ", ".join([tag.name for tag in self.tags.all()])

        # Add categories if they exist
        if self.categories.exists():
            schema["articleSection"] = [
                category.name for category in self.categories.all()
            ]

        return json.dumps(schema, cls=DjangoJSONEncoder)

    def get_sitemap_urls(self, request=None):

        return [
            {
                "location": self.get_full_url(),
                "lastmod": self.last_published_at or self.latest_revision_created_at,
                "changefreq": "weekly",  # Options: always, hourly, daily, weekly, monthly, yearly, never
                "priority": 0.8,  # Homepage might be 1.0, less important pages 0.5 or lower
            }
        ]


class BlogCategory(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(
        verbose_name="slug",
        allow_unicode=True,
        max_length=255,
        help_text="A slug to identify posts by this category",
        unique=True,
    )
    description = models.TextField(blank=True)
    icon = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    # SEO Fields
    meta_title = models.CharField(
        max_length=200,
        blank=True,
        help_text="SEO title for category page (50-60 characters recommended)"
    )
    meta_description = models.TextField(
        blank=True,
        help_text="SEO description for category page (150-160 characters recommended)"
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("description"),
        FieldPanel("icon"),
        FieldPanel("meta_title"),
        FieldPanel("meta_description"),
    ]

    class Meta:
        verbose_name = "Blog Category"
        verbose_name_plural = "Blog Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f"/blog/category/{self.slug}/"
