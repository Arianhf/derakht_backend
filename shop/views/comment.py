# shop/views/comment.py
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.views import list_comments, create_comment
from core.models import Comment
from ..models.product import Product


@api_view(['GET', 'POST'])
@permission_classes([permissions.AllowAny])
def product_comments_list_create(request, slug):
    """
    GET /shop/products/{slug}/comments/ - List product comments
    POST /shop/products/{slug}/comments/ - Create product comment

    This is a product-specific wrapper around the generic comment system.
    """
    # Get the product by slug
    product = get_object_or_404(Product, slug=slug)

    if request.method == 'GET':
        return list_comments(request, product)
    elif request.method == 'POST':
        return create_comment(request, product)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def product_comment_delete(request, slug, comment_id):
    """
    DELETE /shop/products/{slug}/comments/{comment_id}/ - Delete a product comment

    Only the comment author or admin can delete comments.
    """
    # Get the product by slug (to validate it exists)
    product = get_object_or_404(Product, slug=slug)

    # Get the comment
    try:
        comment = Comment.objects.get(
            id=comment_id,
            is_deleted=False
        )
    except Comment.DoesNotExist:
        return Response({
            "code": "COMMENT_NOT_FOUND",
            "message": "Comment not found",
            "severity": "error"
        }, status=status.HTTP_404_NOT_FOUND)

    # Verify the comment belongs to this product
    from django.contrib.contenttypes.models import ContentType
    content_type = ContentType.objects.get_for_model(product)
    if comment.content_type != content_type or str(comment.object_id) != str(product.id):
        return Response({
            "code": "COMMENT_NOT_FOUND",
            "message": "Comment not found for this product",
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
