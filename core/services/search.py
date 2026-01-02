# core/services/search.py
from typing import List, Dict, Any
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q
from django.db.models.functions import Greatest

from blog.models import BlogPost
from shop.models.product import Product
from core.logging_utils import get_logger

logger = get_logger(__name__)


class SearchService:
    """Business logic for search operations"""

    @staticmethod
    def search_blogs(query: str, threshold: float = 0.1, limit: int = 10) -> List[Dict]:
        """
        Search blog posts using trigram similarity

        Args:
            query: Search query string
            threshold: Minimum similarity score (0.0 to 1.0)
            limit: Maximum number of results

        Returns:
            List of blog post dictionaries with metadata
        """
        blogs = (
            BlogPost.objects.live()
            .select_related('header_image')
            .annotate(
                title_similarity=TrigramSimilarity('title', query),
                subtitle_similarity=TrigramSimilarity('subtitle', query),
                intro_similarity=TrigramSimilarity('intro', query),
                similarity=Greatest(
                    'title_similarity',
                    'subtitle_similarity',
                    'intro_similarity',
                )
            )
            .filter(similarity__gte=threshold)
            .order_by('-similarity')
            [:limit]
        )

        results = []
        for blog in blogs:
            # Get header image URL
            header_image_url = None
            if blog.header_image:
                try:
                    rendition = blog.header_image.get_rendition('fill-400x300')
                    header_image_url = rendition.url
                except Exception as e:
                    logger.warning(
                        f"Failed to generate blog rendition: {e}",
                        extra={"extra_data": {"blog_id": blog.id, "error": str(e)}}
                    )
                    header_image_url = blog.header_image.file.url if blog.header_image.file else None

            results.append({
                "id": blog.id,
                "type": "blog",
                "title": blog.title,
                "subtitle": blog.subtitle or '',
                "description": blog.intro,
                "slug": blog.slug,
                "date": blog.date,
                "similarity": round(blog.similarity, 3),
                "featured": blog.featured,
                "hero": blog.hero,
                "reading_time": blog.reading_time,
                "header_image": header_image_url,
                "url": f'/blog/{blog.slug}/'
            })

        return results

    @staticmethod
    def search_products(query: str, threshold: float = 0.1, limit: int = 10) -> List[Dict]:
        """
        Search products using trigram similarity

        Args:
            query: Search query string
            threshold: Minimum similarity score (0.0 to 1.0)
            limit: Maximum number of results

        Returns:
            List of product dictionaries with metadata
        """
        products = (
            Product.objects.filter(is_active=True, is_available=True, is_visible=True)
            .prefetch_related('images')
            .annotate(
                title_similarity=TrigramSimilarity('title', query),
                desc_similarity=TrigramSimilarity('description', query),
                sku_similarity=TrigramSimilarity('sku', query),
                similarity=Greatest(
                    'title_similarity',
                    'desc_similarity',
                    'sku_similarity',
                )
            )
            .filter(similarity__gte=threshold)
            .order_by('-similarity')
            [:limit]
        )

        results = []
        for product in products:
            # Use prefetched images
            feature_image = product.feature_image
            feature_image_url = None
            if feature_image and feature_image.image:
                try:
                    rendition = feature_image.image.get_rendition('fill-400x300')
                    feature_image_url = rendition.url
                except Exception as e:
                    logger.warning(
                        f"Failed to generate product rendition: {e}",
                        extra={"extra_data": {"product_id": str(product.id), "error": str(e)}}
                    )
                    feature_image_url = feature_image.image.file.url if feature_image.image.file else None

            results.append({
                "id": str(product.id),
                "type": "product",
                "title": product.title,
                "description": product.description,
                "slug": product.slug,
                "price": str(product.price),
                "sku": product.sku,
                "similarity": round(product.similarity, 3),
                "stock": product.stock,
                "is_available": product.is_available,
                "feature_image": feature_image_url,
                "url": f'/shop/products/{product.slug}/'
            })

        return results

    @staticmethod
    def search_all(query: str, threshold: float = 0.1, blog_limit: int = 10, product_limit: int = 10) -> Dict[str, Any]:
        """
        Perform global search across all content types

        Args:
            query: Search query string
            threshold: Minimum similarity score (0.0 to 1.0)
            blog_limit: Maximum blog results
            product_limit: Maximum product results

        Returns:
            Dictionary with blog and product results
        """
        if not query or len(query.strip()) < 2:
            return {"blog": [], "products": []}

        query = query.strip()

        logger.info(
            "Global search performed",
            extra={"extra_data": {
                "query": query,
                "threshold": threshold,
            }}
        )

        return {
            "blog": SearchService.search_blogs(query, threshold, blog_limit),
            "products": SearchService.search_products(query, threshold, product_limit),
        }

    @staticmethod
    def combine_and_sort_results(blog_results: List[Dict], product_results: List[Dict]) -> List[Dict]:
        """
        Combine and sort search results by similarity

        Args:
            blog_results: List of blog result dictionaries
            product_results: List of product result dictionaries

        Returns:
            Combined list sorted by similarity (descending)
        """
        all_results = blog_results + product_results
        all_results.sort(key=lambda x: x['similarity'], reverse=True)
        return all_results
