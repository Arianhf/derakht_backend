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
    categories = ParentalManyToManyField(
        "BlogCategory", blank=True, related_name="blogposts"
    )
    related_posts = ParentalManyToManyField(
        "self", blank=True, symmetrical=False, related_name="posts_related_to"
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
        APIField("categories"),
        APIField(
            "related_posts",
            serializer=lambda self: [
                {
                    "id": post.id,
                    "title": post.title,
                    "slug": post.slug,
                    "date": post.date,
                    "intro": post.intro,
                    "header_image": (
                        post.header_image.get_rendition("fill-400x300").url
                        if post.header_image
                        else None
                    ),
                    "jalali_date": (
                        jdatetime.date.fromgregorian(date=post.date).strftime(
                            "%Y-%m-%d"
                        )
                        if post.date
                        else None
                    ),
                    "reading_time": post.reading_time,
                    "owner": (
                        {
                            "first_name": post.owner.first_name if post.owner else "",
                            "last_name": post.owner.last_name if post.owner else "",
                            "profile_image": (
                                post.owner.profile_image.url
                                if post.owner and post.owner.profile_image
                                else None
                            ),
                        }
                        if post.owner
                        else None
                    ),
                }
                for post in self.get_related_posts()
            ],
        ),
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

    def get_related_posts(self, max_items=3):
        """
        Returns related blog posts in the following priority:
        1. Explicitly related posts
        2. Posts with the same categories
        3. Posts with the same tags
        4. Most recent posts (fallback)
        """
        # Exclude self from all queries
        related_items = BlogPost.objects.live().exclude(id=self.id)

        # First, check explicitly defined related posts
        explicit_related = self.related_posts.live()
        if explicit_related.count() >= max_items:
            return explicit_related[:max_items]

        # Keep track of posts we've already included
        included_ids = list(explicit_related.values_list("id", flat=True))

        # Next try to get posts with similar categories (excluding already included posts)
        if self.categories.exists():
            category_posts = (
                related_items.filter(categories__in=self.categories.all())
                .exclude(id__in=included_ids)
                .distinct()
            )

            # Add to our included posts
            included_ids.extend(category_posts.values_list("id", flat=True))

            # Combine with explicit related
            combined_posts = list(explicit_related) + list(category_posts)
            if len(combined_posts) >= max_items:
                return combined_posts[:max_items]
        else:
            category_posts = BlogPost.objects.none()
            combined_posts = list(explicit_related)

        # If we still need more, try to add posts with similar tags
        if self.tags.exists() and len(combined_posts) < max_items:
            tag_posts = (
                related_items.filter(tags__in=self.tags.all())
                .exclude(id__in=included_ids)
                .distinct()
            )

            # Combine the results
            combined_posts = combined_posts + list(tag_posts)
            if len(combined_posts) >= max_items:
                return combined_posts[:max_items]

            # Update included IDs
            included_ids.extend(tag_posts.values_list("id", flat=True))

        # If we still don't have enough posts, add most recent posts
        if len(combined_posts) < max_items:
            recent_posts = related_items.exclude(id__in=included_ids).order_by("-date")

            # Combine all results
            all_posts = combined_posts + list(recent_posts)
            return all_posts[:max_items]

        # Return whatever we have so far
        return combined_posts[:max_items]


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

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("description"),
        FieldPanel("icon"),
    ]

    class Meta:
        verbose_name = "Blog Category"
        verbose_name_plural = "Blog Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f"/blog/category/{self.slug}/"
