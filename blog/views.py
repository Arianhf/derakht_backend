from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from wagtail.api.v2.utils import parse_fields_parameter, BadRequestError
from wagtail.api.v2.views import PagesAPIViewSet, BaseAPIViewSet
from django.urls import path

from blog.category_serializer import BlogCategorySerializer
from blog.models import BlogPost, BlogCategory


class BlogPostAPIViewSet(PagesAPIViewSet):
    model = BlogPost
    authentication_classes = []
    permission_classes = []
    listing_default_fields = PagesAPIViewSet.listing_default_fields + [
        "header_image",
        "reading_time",
        "owner",
        "featured",
        "hero",
        "jalali_date",
        "tags",
        "subtitle",
        "categories",
    ]

    known_query_parameters = frozenset(
        [
            "tag",
            "category",
        ]
    )

    def get_queryset(self):
        queryset = super().get_queryset().specific()

        # For the default list endpoint, exclude featured and hero posts
        if self.action == "listing_view" and not self.request.query_params:
            queryset = queryset.filter(featured=False, hero=False)

        # Filter by category if specified
        category_slug = self.request.query_params.get("category")
        if category_slug:
            try:
                category = BlogCategory.objects.get(slug=category_slug)
                queryset = queryset.filter(categories=category)
            except BlogCategory.DoesNotExist:
                pass

        return queryset

    # Fields to search
    search_fields = ["title", "subtitle", "intro", "body"]

    def featured_view(self, request):
        queryset = self.get_queryset().filter(featured=True)
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def hero_view(self, request):
        queryset = self.get_queryset().filter(hero=True)
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_category(self, request):
        """
        Return blog posts filtered by category
        """
        category_slug = request.query_params.get("slug")
        if not category_slug:
            return Response({"error": "Category slug is required"}, status=400)

        try:
            category = BlogCategory.objects.get(slug=category_slug)
            queryset = self.get_queryset().filter(categories=category)

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        except BlogCategory.DoesNotExist:
            return Response({"error": "Category not found"}, status=404)

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
            path("category/", cls.as_view({"get": "by_category"}), name="by_category"),
        ]

    def get_serializer_class(self):
        request = self.request

        # Get model
        if self.action in ["listing_view", "featured_view", "hero_view", "by_category"]:
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


class BlogCategoryAPIViewSet(BaseAPIViewSet):
    """API endpoint for blog categories"""

    model = BlogCategory

    def get_queryset(self):
        return BlogCategory.objects.all()

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        return get_object_or_404(self.get_queryset(), **filter_kwargs)

    def listing_view(self, request):
        queryset = self.get_queryset()
        serializer = BlogCategorySerializer(queryset, many=True)
        return Response(serializer.data)

    def detail_view(self, request, pk):
        instance = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = BlogCategorySerializer(instance)
        return Response(serializer.data)

    @classmethod
    def get_urlpatterns(cls):
        """
        This returns a list of URL patterns for the endpoint
        """
        return [
            path("", cls.as_view({"get": "listing_view"}), name="listing"),
            path("<int:pk>/", cls.as_view({"get": "detail_view"}), name="detail"),
        ]
