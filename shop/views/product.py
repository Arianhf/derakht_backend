# shop/views/product.py
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models import Product, Category
from ..serializers.product import ProductSerializer, CategorySerializer


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for products
    """

    queryset = Product.objects.filter(is_active=True, is_available=True)
    serializer_class = ProductSerializer
    lookup_field = "slug"
    permission_classes = [permissions.AllowAny]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["title", "description", "sku"]
    ordering_fields = ["price", "created_at", "title"]
    filterset_fields = ["is_available", "min_age", "max_age"]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by search query
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(title__icontains=search)

        # Filter by price range
        min_price = self.request.query_params.get("min_price")
        if min_price:
            queryset = queryset.filter(price__gte=min_price)

        max_price = self.request.query_params.get("max_price")
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        # Filter by category
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category_id=category)

        return queryset

    @action(detail=False, methods=["get"])
    def by_age(self, request):
        """
        Filter products by age
        """
        age = request.query_params.get("age")
        if not age:
            return Response(
                {"error": "Age parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            age = int(age)
        except ValueError:
            return Response(
                {"error": "Age must be a valid integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.get_queryset().filter(min_age__lte=age, max_age__gte=age)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def age_filter(self, request):
        """
        Filter products by age range
        """
        min_age = request.query_params.get("min")
        max_age = request.query_params.get("max")

        queryset = self.get_queryset()

        if min_age:
            try:
                min_age = int(min_age)
                queryset = queryset.filter(max_age__gte=min_age)
            except ValueError:
                return Response(
                    {"error": "Minimum age must be a valid integer"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if max_age:
            try:
                max_age = int(max_age)
                queryset = queryset.filter(min_age__lte=max_age)
            except ValueError:
                return Response(
                    {"error": "Maximum age must be a valid integer"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(
        detail=False, url_path="by_category/(?P<category_id>[^/.]+)", methods=["get"]
    )
    def by_category(self, request, category_id=None):
        """
        Get products by category
        """
        queryset = self.get_queryset().filter(category_id=category_id)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for categories
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
