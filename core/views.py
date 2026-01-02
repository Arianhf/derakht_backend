# core/views.py
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.search import TrigramSimilarity
from django.core.cache import cache
from django.db.models import Q, Value, FloatField, CharField
from django.db.models.functions import Greatest
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
import hashlib

from blog.models import BlogPost
from shop.models.product import Product
from .models import FeatureFlag, Comment
from .serializers import FeatureFlagSerializer, CommentSerializer, CreateCommentSerializer
from .utils import is_feature_enabled
from .logging_utils import get_logger
from .services.search import SearchService

logger = get_logger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def feature_flags(request):
    """Get all feature flags with caching"""
    cache_key = 'feature_flags:all'
    flags_data = cache.get(cache_key)

    if flags_data is None:
        flags = FeatureFlag.objects.all()
        serializer = FeatureFlagSerializer(flags, many=True)
        flags_data = serializer.data
        # Cache for 5 minutes (300 seconds)
        cache.set(cache_key, flags_data, 300)

    return Response(flags_data)


@api_view(['GET'])
@permission_classes([AllowAny])
def feature_flag_detail(request, name):
    """Get a specific feature flag by name"""
    enabled = is_feature_enabled(name)
    return Response({"name": name, "enabled": enabled})


@api_view(['GET'])
@permission_classes([AllowAny])
def global_search(request):
    """
    Global search endpoint that searches across blogs and products with fuzzy matching.
    Results are cached for 5 minutes to improve performance.

    Query parameters:
    - q: Search query (required)
    - threshold: Minimum similarity threshold (0.0 to 1.0, default: 0.1)
    - page: Page number for pagination
    - page_size: Results per page (default: 10, max: 50)

    Returns combined results from blogs and products ordered by relevance.
    """
    query = request.GET.get('q', '').strip()

    if not query:
        return Response({
            'error': 'Search query parameter "q" is required'
        }, status=400)

    # Get threshold parameter (default 0.1 for more flexible fuzzy matching)
    try:
        threshold = float(request.GET.get('threshold', 0.1))
        threshold = max(0.0, min(1.0, threshold))  # Clamp between 0 and 1
    except (ValueError, TypeError):
        threshold = 0.1

    # Create cache key from query and threshold
    cache_key = f"search:{hashlib.md5(f'{query}:{threshold}'.encode()).hexdigest()}"
    cached_results = cache.get(cache_key)

    if cached_results is not None:
        # Return cached results with pagination
        all_results = cached_results
    else:
        # Use SearchService to perform search
        blog_list = SearchService.search_blogs(query, threshold, limit=100)
        product_list = SearchService.search_products(query, threshold, limit=100)

        # Combine and sort results
        all_results = SearchService.combine_and_sort_results(blog_list, product_list)

        # Cache the results for 5 minutes (300 seconds)
        cache.set(cache_key, all_results, 300)

    # Pagination
    page_size = int(request.GET.get('page_size', 10))
    page_size = min(page_size, 50)  # Max 50 per page

    paginator = PageNumberPagination()
    paginator.page_size = page_size

    # Paginate the results
    paginated_results = paginator.paginate_queryset(all_results, request)

    # Calculate counts from all_results (works for both cached and fresh results)
    blog_count = sum(1 for r in all_results if r.get('type') == 'blog')
    product_count = sum(1 for r in all_results if r.get('type') == 'product')

    return paginator.get_paginated_response({
        'query': query,
        'threshold': threshold,
        'total_results': len(all_results),
        'blog_count': blog_count,
        'product_count': product_count,
        'results': paginated_results
    })


# Generic Comment Views
class CommentPagination(PageNumberPagination):
    """
    Custom pagination for comments - 20 items per page as recommended
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def get_content_object_or_404(app_label, model_name, identifier):
    """
    Helper function to get a content object by app_label, model_name, and identifier.
    Supports both slug and UUID lookups.
    """
    try:
        content_type = ContentType.objects.get(app_label=app_label, model=model_name)
    except ContentType.DoesNotExist:
        return None, f"Content type {app_label}.{model_name} not found"

    model_class = content_type.model_class()

    # Try to get the object by slug first, then by UUID
    try:
        # Try slug lookup
        if hasattr(model_class, 'slug'):
            obj = get_object_or_404(model_class, slug=identifier)
        else:
            # Try UUID lookup
            obj = get_object_or_404(model_class, id=identifier)
        return obj, None
    except Exception as e:
        return None, f"Object not found: {str(e)}"


@api_view(['GET', 'POST'])
@permission_classes([permissions.AllowAny])
def comments_list_create(request, app_label, model_name, identifier):
    """
    GET /comments/{app_label}/{model_name}/{identifier}/ - List comments
    POST /comments/{app_label}/{model_name}/{identifier}/ - Create comment

    Examples:
    - GET /comments/shop/product/my-product-slug/
    - POST /comments/blog/blogpost/my-blog-slug/
    """
    # Get the content object
    content_object, error = get_content_object_or_404(app_label, model_name, identifier)
    if error:
        return Response({
            "code": "OBJECT_NOT_FOUND",
            "message": error,
            "severity": "error"
        }, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return list_comments(request, content_object)
    elif request.method == 'POST':
        return create_comment(request, content_object)


def list_comments(request, content_object):
    """
    List all approved comments for a content object.
    Only approved comments are returned to non-admin users.
    """
    # Get content type
    content_type = ContentType.objects.get_for_model(content_object)

    # Get comments for this object
    queryset = Comment.objects.filter(
        content_type=content_type,
        object_id=content_object.id,
        is_deleted=False,
    )

    # Only show approved comments to non-staff users
    if not request.user.is_staff:
        queryset = queryset.filter(is_approved=True)

    # Order by newest first
    queryset = queryset.order_by('-created_at')

    # Paginate
    paginator = CommentPagination()
    page = paginator.paginate_queryset(queryset, request)

    if page is not None:
        serializer = CommentSerializer(page, many=True)
        # Custom pagination response format
        return Response({
            "items": serializer.data,
            "total": paginator.page.paginator.count,
            "page": paginator.page.number,
            "pages": paginator.page.paginator.num_pages,
        })

    serializer = CommentSerializer(queryset, many=True)
    return Response({
        "items": serializer.data,
        "total": queryset.count(),
        "page": 1,
        "pages": 1,
    })


def create_comment(request, content_object):
    """
    Create a new comment for a content object.
    Supports both authenticated and anonymous users.
    """
    # Validate the request data
    serializer = CreateCommentSerializer(data=request.data)

    if not serializer.is_valid():
        # Extract error details
        errors = serializer.errors

        # Check for specific validation errors
        if 'text' in errors:
            error_detail = errors['text'][0]

            # If it's our custom validation error (dict format)
            if isinstance(error_detail, dict):
                return Response(error_detail, status=status.HTTP_400_BAD_REQUEST)

            # Handle DRF's built-in validation errors
            error_str = str(error_detail)
            if 'too short' in error_str.lower() or 'min_length' in error_str.lower():
                return Response({
                    "code": "COMMENT_TOO_SHORT",
                    "message": "Comment text is too short",
                    "severity": "error",
                    "details": {
                        "field": "text",
                        "limit": 10
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            elif 'too long' in error_str.lower() or 'max_length' in error_str.lower():
                return Response({
                    "code": "COMMENT_TOO_LONG",
                    "message": "Comment text is too long",
                    "severity": "error",
                    "details": {
                        "field": "text",
                        "limit": 1000
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

        # Generic validation error
        return Response({
            "code": "COMMENT_SUBMIT_FAILED",
            "message": "Failed to submit comment",
            "severity": "error",
            "details": errors
        }, status=status.HTTP_400_BAD_REQUEST)

    # Get content type
    content_type = ContentType.objects.get_for_model(content_object)

    # Create the comment
    comment_data = {
        'content_type': content_type,
        'object_id': content_object.id,
        'text': serializer.validated_data['text'],
    }

    # Set user if authenticated
    if request.user.is_authenticated:
        comment_data['user'] = request.user
        # user_name will be set automatically in the model's save method
    else:
        # Anonymous user
        comment_data['user'] = None
        comment_data['user_name'] = "کاربر ناشناس"

    # Set approval status - auto-approve for verified/staff users
    if request.user.is_authenticated and (request.user.is_staff or getattr(request.user, 'is_verified', False)):
        comment_data['is_approved'] = True
    else:
        comment_data['is_approved'] = False

    # Create the comment
    comment = Comment.objects.create(**comment_data)

    # Return the created comment
    response_serializer = CommentSerializer(comment)
    return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def comment_delete(request, comment_id):
    """
    DELETE /comments/{comment_id}/ - Delete a comment

    Only the comment author or admin can delete comments.
    """
    # Get the comment
    try:
        comment = Comment.objects.get(
            id=comment_id,
            is_deleted=False
        )
    except Comment.DoesNotExist:
        logger.warning(
            "Comment not found for deletion",
            extra={
                "extra_data": {
                    "comment_id": str(comment_id),
                    "user_id": request.user.id,
                }
            },
        )
        return Response({
            "code": "COMMENT_NOT_FOUND",
            "message": "Comment not found",
            "severity": "error"
        }, status=status.HTTP_404_NOT_FOUND)

    # Check permissions
    # User must be the comment author or an admin
    if comment.user != request.user and not request.user.is_staff:
        return Response({
            "code": "FORBIDDEN",
            "message": "You don't have permission to delete this comment",
            "severity": "error"
        }, status=status.HTTP_403_FORBIDDEN)

    # Soft delete
    comment.is_deleted = True
    comment.save()

    # Return 204 No Content
    return Response(status=status.HTTP_204_NO_CONTENT)