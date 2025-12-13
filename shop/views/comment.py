# shop/views/comment.py
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from ..models import Product, ProductComment
from ..serializers.comment import (
    ProductCommentSerializer,
    CreateProductCommentSerializer,
)


class CommentPagination(PageNumberPagination):
    """
    Custom pagination for comments - 20 items per page as recommended
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET', 'POST'])
@permission_classes([permissions.AllowAny])
def product_comments(request, slug):
    """
    GET /shop/products/{slug}/comments/ - List all approved comments for a product
    POST /shop/products/{slug}/comments/ - Create a new comment for a product
    """
    if request.method == 'GET':
        return list_product_comments(request, slug)
    elif request.method == 'POST':
        return create_product_comment(request, slug)


def list_product_comments(request, slug):
    """
    List all approved comments for a product.
    Only approved comments are returned to non-admin users.
    """
    # Get the product
    product = get_object_or_404(Product, slug=slug, is_active=True)

    # Get comments for this product
    queryset = ProductComment.objects.filter(
        product=product,
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
        serializer = ProductCommentSerializer(page, many=True)
        # Custom pagination response format
        return Response({
            "items": serializer.data,
            "total": paginator.page.paginator.count,
            "page": paginator.page.number,
            "pages": paginator.page.paginator.num_pages,
        })

    serializer = ProductCommentSerializer(queryset, many=True)
    return Response({
        "items": serializer.data,
        "total": queryset.count(),
        "page": 1,
        "pages": 1,
    })


def create_product_comment(request, slug):
    """
    POST /shop/products/{slug}/comments/

    Create a new comment for a product.
    Supports both authenticated and anonymous users.
    """
    # Get the product
    product = get_object_or_404(Product, slug=slug, is_active=True)

    # Validate the request data
    serializer = CreateProductCommentSerializer(data=request.data)

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

    # Create the comment
    comment_data = {
        'product': product,
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
    comment = ProductComment.objects.create(**comment_data)

    # Return the created comment
    response_serializer = ProductCommentSerializer(comment)
    return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_product_comment(request, slug, comment_id):
    """
    DELETE /shop/products/{slug}/comments/{comment_id}/

    Delete a product comment.
    Only the comment author or admin can delete comments.
    """
    # Get the product
    product = get_object_or_404(Product, slug=slug, is_active=True)

    # Get the comment
    try:
        comment = ProductComment.objects.get(
            id=comment_id,
            product=product,
            is_deleted=False
        )
    except ProductComment.DoesNotExist:
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
