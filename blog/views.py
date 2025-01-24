from wagtail.api.v2.views import PagesAPIViewSet

from blog.serializers import BlogPostSerializer


class BlogPostAPIViewSet(PagesAPIViewSet):
    base_serializer_class = BlogPostSerializer

    def get_queryset(self):
        return super().get_queryset().specific()

    # Add fields to the API
    meta_fields = PagesAPIViewSet.meta_fields + [
        'subtitle',
        'intro',
        'body',
        'date',
        'tags',
        'header_image',
        'alternative_titles',
    ]
    body_fields = PagesAPIViewSet.body_fields + [
        'subtitle',
        'intro',
        'body',
        'date',
        'tags',
        'header_image',
        'alternative_titles',
    ]
    # Fields to search
    search_fields = ['title', 'subtitle', 'intro', 'body']


class BlogIndexPageAPIViewSet(PagesAPIViewSet):
    def get_queryset(self):
        return super().get_queryset().specific()
