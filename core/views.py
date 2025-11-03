# core/views.py
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q, Value, FloatField, CharField
from django.db.models.functions import Greatest
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from blog.models import BlogPost
from shop.models.product import Product
from .models import FeatureFlag
from .serializers import FeatureFlagSerializer
from .utils import is_feature_enabled


@api_view(['GET'])
@permission_classes([AllowAny])
def feature_flags(request):
    """Get all feature flags"""
    flags = FeatureFlag.objects.all()
    serializer = FeatureFlagSerializer(flags, many=True)
    return Response(serializer.data)


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

    # Search blogs using trigram similarity
    blog_results = BlogPost.objects.live().select_related('header_image').annotate(
        title_similarity=TrigramSimilarity('title', query),
        subtitle_similarity=TrigramSimilarity('subtitle', query),
        intro_similarity=TrigramSimilarity('intro', query),
        # Calculate the maximum similarity across all fields
        similarity=Greatest(
            'title_similarity',
            'subtitle_similarity',
            'intro_similarity',
        )
    ).filter(
        similarity__gte=threshold
    )

    # Search products using trigram similarity
    product_results = Product.objects.filter(
        is_active=True,
        is_available=True
    ).prefetch_related('images').annotate(
        title_similarity=TrigramSimilarity('title', query),
        description_similarity=TrigramSimilarity('description', query),
        sku_similarity=TrigramSimilarity('sku', query),
        # Calculate the maximum similarity across all fields
        similarity=Greatest(
            'title_similarity',
            'description_similarity',
            'sku_similarity',
        )
    ).filter(
        similarity__gte=threshold
    )

    # Combine results
    blog_list = []
    for blog in blog_results:
        # Get header image URL if it exists
        header_image_url = None
        if blog.header_image:
            try:
                # Get a medium-sized rendition for the search results
                rendition = blog.header_image.get_rendition('fill-400x300')
                header_image_url = rendition.url
            except:
                # Fallback to original if rendition fails
                header_image_url = blog.header_image.file.url if blog.header_image.file else None

        blog_list.append({
            'id': blog.id,
            'type': 'blog',
            'title': blog.title,
            'subtitle': blog.subtitle or '',
            'description': blog.intro,
            'slug': blog.slug,
            'date': blog.date,
            'similarity': round(blog.similarity, 3),
            'featured': blog.featured,
            'hero': blog.hero,
            'reading_time': blog.reading_time,
            'header_image': header_image_url,
            'url': f'/blog/{blog.slug}/'
        })

    product_list = []
    for product in product_results:
        # Get feature image URL if it exists
        feature_image_url = None
        feature_img = product.feature_image
        if feature_img and feature_img.image:
            try:
                # Get a medium-sized rendition for the search results
                rendition = feature_img.image.get_rendition('fill-400x300')
                feature_image_url = rendition.url
            except:
                # Fallback to original if rendition fails
                feature_image_url = feature_img.image.file.url if feature_img.image.file else None

        product_list.append({
            'id': product.id,
            'type': 'product',
            'title': product.title,
            'description': product.description,
            'slug': product.slug,
            'price': str(product.price),
            'sku': product.sku,
            'similarity': round(product.similarity, 3),
            'stock': product.stock,
            'is_available': product.is_available,
            'feature_image': feature_image_url,
            'url': f'/shop/products/{product.slug}/'
        })

    # Combine and sort by similarity (relevance)
    all_results = blog_list + product_list
    all_results.sort(key=lambda x: x['similarity'], reverse=True)

    # Pagination
    page_size = int(request.GET.get('page_size', 10))
    page_size = min(page_size, 50)  # Max 50 per page

    paginator = PageNumberPagination()
    paginator.page_size = page_size

    # Paginate the results
    paginated_results = paginator.paginate_queryset(all_results, request)

    return paginator.get_paginated_response({
        'query': query,
        'threshold': threshold,
        'total_results': len(all_results),
        'blog_count': len(blog_list),
        'product_count': len(product_list),
        'results': paginated_results
    })