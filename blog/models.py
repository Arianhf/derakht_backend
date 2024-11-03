import jdatetime
from modelcluster.fields import ParentalKey
from django.db import models
from wagtail.models import Page, Orderable
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.search import index
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.models import TaggedItemBase

from blog.panels import JalaliDatePanel


class BlogIndexPage(Page):
    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro')
    ]

    def get_context(self, request):
        context = super().get_context(request)
        blogposts = BlogPost.objects.child_of(self).live().order_by('-date')

        # Filter by tag
        tag = request.GET.get('tag')
        if tag:
            blogposts = blogposts.filter(tags__name=tag)

        context['blogposts'] = blogposts
        return context


class BlogPostTag(TaggedItemBase):
    content_object = ParentalKey(
        'BlogPost',
        related_name='tagged_items',
        on_delete=models.CASCADE
    )


class BlogPost(Page):
    date = models.DateField("Post date")
    subtitle = models.CharField(max_length=250, blank=True)
    intro = models.CharField(max_length=250)
    header_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    body = RichTextField(blank=True)
    tags = ClusterTaggableManager(through=BlogPostTag, blank=True)

    # Property to get Jalali date
    @property
    def jalali_date(self):
        if self.date:
            return jdatetime.date.fromgregorian(date=self.date)
        return None

    search_fields = Page.search_fields + [
        index.SearchField('intro'),
        index.SearchField('subtitle'),
        index.SearchField('body'),
    ]

    content_panels = Page.content_panels + [
        JalaliDatePanel('date'),
        FieldPanel('subtitle'),
        FieldPanel('intro'),
        FieldPanel('header_image'),
        FieldPanel('body'),
        FieldPanel('tags'),
    ]
