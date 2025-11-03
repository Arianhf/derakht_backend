# core/views.py
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q, Value, FloatField
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
    blog_results = BlogPost.objects.live().annotate(
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
    ).values(
        'id',
        'title',
        'subtitle',
        'intro',
        'slug',
        'date',
        'similarity',
        'featured',
        'hero',
        'reading_time',
    ).annotate(
        type=Value('blog', output_field=FloatField())
    )

    # Search products using trigram similarity
    product_results = Product.objects.filter(
        is_active=True,
        is_available=True
    ).annotate(
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
    ).values(
        'id',
        'title',
        'description',
        'slug',
        'price',
        'sku',
        'similarity',
        'stock',
        'is_available',
    ).annotate(
        type=Value('product', output_field=FloatField())
    )

    # Combine results
    blog_list = [
        {
            'id': item['id'],
            'type': 'blog',
            'title': item['title'],
            'subtitle': item.get('subtitle', ''),
            'description': item['intro'],
            'slug': item['slug'],
            'date': item['date'],
            'similarity': round(item['similarity'], 3),
            'featured': item['featured'],
            'hero': item['hero'],
            'reading_time': item['reading_time'],
            'url': f'/blog/{item["slug"]}/'
        }
        for item in blog_results
    ]

    product_list = [
        {
            'id': item['id'],
            'type': 'product',
            'title': item['title'],
            'description': item['description'],
            'slug': item['slug'],
            'price': str(item['price']),
            'sku': item['sku'],
            'similarity': round(item['similarity'], 3),
            'stock': item['stock'],
            'is_available': item['is_available'],
            'url': f'/shop/products/{item["slug"]}/'
        }
        for item in product_results
    ]

    # Combine and sort by similarity (relevance)
    all_results = blog_list + product_list
    all_results.sort(key=lambda x: x['similarity'], reverse=True)

    # Pagination
    page_size = int(request.GET.get('page_size', 10))
    page_size = min(page_size, 50)  # Max 50 per page

    paginator = PageNumberPagination()
    paginator.page_size = page_size

    # Use request to paginate
    from rest_framework.request import Request
    drf_request = Request(request)
    paginated_results = paginator.paginate_queryset(all_results, drf_request)

    return paginator.get_paginated_response({
        'query': query,
        'threshold': threshold,
        'total_results': len(all_results),
        'blog_count': len(blog_list),
        'product_count': len(product_list),
        'results': paginated_results
    })