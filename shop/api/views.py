from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    OrderSerializer,
    PaymentSerializer,
    CartItemSerializer,
    CartDetailsSerializer,
    OrderStatusHistorySerializer, ProductListSerializer, ProductDetailSerializer
)
from ..models import Order, Payment, Product
from ..services import PaymentService, CartService


class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def request_payment(self, request, pk=None):
        order = self.get_object()
        payment_service = PaymentService()

        # Create payment
        payment = payment_service.create_payment(order)

        # Request payment
        result = payment_service.request_payment(payment)

        if result['success']:
            return Response({
                'redirect_url': result['redirect_url']
            })

        return Response(
            {'error': result['message']},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        try:
            order.cancel()
            return Response({'status': 'success'})
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def confirm_delivery(self, request, pk=None):
        order = self.get_object()
        try:
            order.mark_delivered()
            return Response({'status': 'success'})
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        order = self.get_object()
        history = order.status_history.all()
        return Response(OrderStatusHistorySerializer(history, many=True).data)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(order__user=self.request.user)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        payment = self.get_object()
        payment_service = PaymentService()

        result = payment_service.verify_payment(payment, request.data)

        if result['success']:
            return Response({'ref_id': result['ref_id']})

        return Response(
            {'error': result['message']},
            status=status.HTTP_400_BAD_REQUEST
        )


class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def get_cart_service(self):
        return CartService(self.request.user)

    @action(detail=False, methods=['get'])
    def details(self, request):
        cart_service = self.get_cart_service()
        cart_details = cart_service.get_cart_details()
        return Response(CartDetailsSerializer(cart_details).data)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        cart_service = self.get_cart_service()
        try:
            product_id = request.data.get('product_id')
            quantity = int(request.data.get('quantity', 1))

            product = Product.objects.get(id=product_id)
            cart_item = cart_service.add_item(product, quantity)

            return Response(CartItemSerializer(cart_item).data)
        except (Product.DoesNotExist, ValidationError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def update_quantity(self, request):
        cart_service = self.get_cart_service()
        try:
            product_id = request.data.get('product_id')
            quantity = int(request.data.get('quantity', 0))

            product = Product.objects.get(id=product_id)
            cart_item = cart_service.update_quantity(product, quantity)

            if cart_item:
                return Response(CartItemSerializer(cart_item).data)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except (Product.DoesNotExist, ValidationError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        cart_service = self.get_cart_service()
        try:
            product_id = request.data.get('product_id')
            product = Product.objects.get(id=product_id)
            cart_service.remove_item(product)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Product.DoesNotExist as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def clear(self, request):
        cart_service = self.get_cart_service()
        cart_service.clear()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        cart_service = self.get_cart_service()
        try:
            shipping_address = request.data.get('shipping_address')
            phone_number = request.data.get('phone_number')

            if not shipping_address or not phone_number:
                raise ValidationError(
                    _('Shipping address and phone number are required')
                )

            order = cart_service.checkout(
                shipping_address=shipping_address,
                phone_number=phone_number
            )

            return Response(OrderSerializer(order).data)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'sku']
    ordering_fields = ['price', 'created_at', 'title']
    filterset_fields = ['is_available', 'min_age', 'max_age']
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductDetailSerializer

    @action(detail=False, methods=['get'])
    def by_age(self, request):
        """Filter products by age range"""
        target_age = request.query_params.get('age')

        if not target_age or not target_age.isdigit():
            return Response(
                {"error": "Please provide a valid age parameter"},
                status=status.HTTP_400_BAD_REQUEST
            )

        target_age = int(target_age)

        # Find products where the target age falls within the product's age range
        queryset = self.queryset.filter(
            Q(min_age__lte=target_age, max_age__gte=target_age) |  # Within range
            Q(min_age__lte=target_age, max_age__isnull=True) |  # Only min age defined
            Q(min_age__isnull=True, max_age__gte=target_age) |  # Only max age defined
            Q(min_age__isnull=True, max_age__isnull=True)  # No age limit
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ProductListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ProductListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def age_filter(self, request):
        """Filter products by age range parameters (min_age and max_age)"""
        min_age = request.query_params.get('min')
        max_age = request.query_params.get('max')

        if not min_age or not max_age or not min_age.isdigit() or not max_age.isdigit():
            return Response(
                {"error": "Please provide valid min and max age parameters"},
                status=status.HTTP_400_BAD_REQUEST
            )

        min_age = int(min_age)
        max_age = int(max_age)

        # Find products with overlapping age ranges
        queryset = self.queryset.filter(
            # Product range overlaps with requested range
            (Q(min_age__lte=max_age) & Q(max_age__gte=min_age)) |
            # No max age specified for product (e.g., 3+)
            (Q(min_age__lte=max_age) & Q(max_age__isnull=True)) |
            # No min age specified for product (e.g., 0-5)
            (Q(min_age__isnull=True) & Q(max_age__gte=min_age)) |
            # No age range specified for product
            (Q(min_age__isnull=True) & Q(max_age__isnull=True))
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ProductListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ProductListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
