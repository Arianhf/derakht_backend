import json

import jdatetime
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from rest_framework.fields import DateField
from taggit.models import TaggedItemBase
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.api import APIField
from wagtail.fields import RichTextField
from wagtail.models import Page, Orderable
from wagtail.search import index

from blog.panels import JalaliDatePanel
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

        context["blogposts"] = blogposts
        return context

    def get_tag_url(self, tag):
        return f"{self.url}?tag={tag.slug}"


class BlogPostTag(TaggedItemBase):
    content_object = ParentalKey(
        "BlogPost", related_name="tagged_items", on_delete=models.CASCADE
    )


class BlogPost(Page):
    date = models.DateField("Post date")
    subtitle = models.CharField(max_length=250, blank=True)
    intro = models.CharField(max_length=250)
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

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("subtitle"),
        index.SearchField("body"),
        index.SearchField("alternative_titles"),
    ]

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                JalaliDatePanel("date"),
                FieldPanel("subtitle"),
                FieldPanel("alternative_titles"),
                FieldPanel("featured"),
                FieldPanel("hero"),
            ],
            heading="Post Information",
        ),
        FieldPanel("intro"),
        FieldPanel("header_image"),
        FieldPanel("body"),
        FieldPanel("tags"),
        FieldPanel("reading_time"),
    ]

    api_fields = [
        APIField("date", serializer=DateField(format="%d %B %Y")),
        APIField("subtitle"),
        APIField("intro"),
        APIField("alternative_titles", serializer=CommaSeparatedListField()),
        APIField("header_image"),
        APIField("body", serializer=RichTextFieldSerializer()),
        APIField("tags"),
        APIField("jalali_date", serializer=JalaliDateField()),
        APIField("reading_time"),
        APIField("owner", serializer=SmallUserSerializer()),
        APIField("featured"),
        APIField("hero"),
    ]

    # Property to get Jalali date
    @property
    def jalali_date(self):
        if self.date:
            return jdatetime.date.fromgregorian(date=self.date)
        return None

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
