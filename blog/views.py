from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from wagtail.api.v2.utils import parse_fields_parameter, BadRequestError
from wagtail.api.v2.views import PagesAPIViewSet, BaseAPIViewSet
from wagtail.models import Page
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

        # Get pagination parameters
        page_number = request.GET.get("page", 1)
        page_size = request.GET.get("size", 10)

        # Paginate the queryset
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page_number)

        # Serialize the data
        serializer = BlogCategorySerializer(page_obj, many=True)

        response_data = {
            "items": serializer.data,
            "total": paginator.count,
            "page": int(page_number),
            "size": int(page_size),
        }

        return Response(response_data)

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


# blog/views.py - Add this to your existing views file


@api_view(
    ["GET"],
)
@permission_classes((AllowAny,))
def related_posts(request, post_id):
    """
    API endpoint to fetch related posts for a given blog post ID.

    Returns posts in this priority:
    1. Explicitly related posts
    2. Posts with the same categories
    3. Posts with the same tags
    4. Most recent posts

    Usage: /api/v2/related-posts/<post_id>/
    """
    try:
        post_id = int(post_id)
    except ValueError:
        return Response({"error": "Invalid post ID format"}, status=400)

    # Get the blog post
    post = get_object_or_404(
        Page.objects.specific(), id=post_id, content_type__model="blogpost"
    )

    # Make sure it's specifically a BlogPost
    if not isinstance(post, BlogPost):
        return Response({"error": "ID does not correspond to a blog post"}, status=400)

    # Limit to a maximum of 3 related posts (or user-specified limit)
    max_items = int(request.GET.get("limit", 3))
    result = []
    included_ids = [post.id]  # Start with current post ID

    # Priority 1: Explicitly related posts
    if hasattr(post, "related_posts") and post.related_posts.exists():
        explicit_related = post.related_posts.live()
        result.extend(format_posts(explicit_related, "explicit"))
        included_ids.extend([p["id"] for p in result])

        # If we have enough explicitly related posts, return them
        if len(result) >= max_items:
            return Response(result[:max_items])

    # Priority 2: Posts with the same categories
    if hasattr(post, "categories") and post.categories.exists():
        needed = max_items - len(result)
        category_posts = (
            BlogPost.objects.live()
            .filter(categories__in=post.categories.all())
            .exclude(id__in=included_ids)
            .distinct()
            .order_by("-date")[:needed]
        )

        category_result = format_posts(category_posts, "category")
        result.extend(category_result)
        included_ids.extend([p["id"] for p in category_result])

        if len(result) >= max_items:
            return Response(result[:max_items])

    # Priority 3: Posts with the same tags
    if hasattr(post, "tags") and post.tags.exists():
        needed = max_items - len(result)
        tag_posts = (
            BlogPost.objects.live()
            .filter(tags__in=post.tags.all())
            .exclude(id__in=included_ids)
            .distinct()
            .order_by("-date")[:needed]
        )

        tag_result = format_posts(tag_posts, "tag")
        result.extend(tag_result)
        included_ids.extend([p["id"] for p in tag_result])

        if len(result) >= max_items:
            return Response(result[:max_items])

    # Priority 4: Recent posts (fallback)
    needed = max_items - len(result)
    if needed > 0:
        recent_posts = (
            BlogPost.objects.live()
            .exclude(id__in=included_ids)
            .order_by("-date")[:needed]
        )

        result.extend(format_posts(recent_posts, "recent"))

    return Response(result[:max_items])


def format_posts(posts, relationship_type):
    """
    Format a queryset of posts into a list of dictionaries for API response.

    Args:
        posts: A queryset of BlogPost objects
        relationship_type: String indicating how these posts are related

    Returns:
        List of formatted post dictionaries
    """
    formatted_posts = []
    for post in posts:
        formatted_posts.append(
            {
                "id": post.id,
                "title": post.title,
                "slug": post.slug,
                "intro": getattr(post, "intro", ""),
                "header_image": (
                    post.header_image.get_rendition("fill-400x300").url
                    if hasattr(post, "header_image") and post.header_image
                    else None
                ),
                "date": getattr(post, "date", None) and post.date.isoformat(),
                "jalali_date": (
                    post.jalali_date.strftime("%Y-%m-%d")
                    if hasattr(post, "jalali_date") and post.jalali_date
                    else None
                ),
                "reading_time": getattr(post, "reading_time", 0),
                "relationship_type": relationship_type,
            }
        )
    return formatted_posts
