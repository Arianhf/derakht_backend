from rest_framework.decorators import action
from rest_framework.response import Response
from wagtail.api.v2.utils import parse_fields_parameter, BadRequestError
from wagtail.api.v2.views import PagesAPIViewSet
from django.urls import path
from blog.models import BlogPost


class BlogPostAPIViewSet(PagesAPIViewSet):
    model = BlogPost
    authentication_classes = []
    listing_default_fields = PagesAPIViewSet.listing_default_fields + [
        "header_image",
        "reading_time",
        "owner",
        "featured",
        "hero",
        "jalali_date",
        "tags",
        "subtitle"
    ]

    def get_queryset(self):
        queryset = super().get_queryset().specific()

        # For the default list endpoint, exclude featured and hero posts
        if self.action == 'listing_view':
            queryset = queryset.filter(featured=False, hero=False)

        return queryset

    # Fields to search
    search_fields = ['title', 'subtitle', 'intro', 'body']

    def featured_view(self, request):
        queryset = self.get_queryset().filter(featured=True)
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def hero_view(self, request):
        queryset = self.get_queryset().filter(hero=True).first()
        if queryset:
            serializer = self.get_serializer(queryset)
            return Response(serializer.data)
        return Response({})

    @classmethod
    def get_urlpatterns(cls):
        """
        This returns a list of URL patterns for the endpoint
        """
        return [
            path("", cls.as_view({"get": "listing_view"}), name="listing"),
            path("<int:pk>/", cls.as_view({"get": "detail_view"}), name="detail"),
            path("find/", cls.as_view({"get": "find_view"}), name="find"),
            path("featured/", cls.as_view({"get": "featured_view"}), name="featured"),
            path("hero/", cls.as_view({"get": "hero_view"}), name="hero"),
            # path('<slug:slug>/', cls.as_view({'get': 'detail_view'}), name='detail'),
        ]


    def get_serializer_class(self):
        request = self.request

        # Get model
        if self.action in ["listing_view", "featured_view", "hero_view"]:
            model = self.get_queryset().model
        else:
            model = type(self.get_object())

        # Fields
        if "fields" in request.GET:
            try:
                fields_config = parse_fields_parameter(request.GET["fields"])
            except ValueError as e:
                raise BadRequestError("fields error: %s" % str(e))
        else:
            # Use default fields
            fields_config = []

        if self.action in ["listing_view", "featured_view", "hero_view"]:
            show_details = False
        else:
            show_details = True

        return self._get_serializer_class(
            self.request.wagtailapi_router,
            model,
            fields_config,
            show_details=show_details,
        )

class BlogIndexPageAPIViewSet(PagesAPIViewSet):
    # base_serializer_class = BlogPostSerializer
    authentication_classes = []
    def get_queryset(self):
        return super().get_queryset().specific()
