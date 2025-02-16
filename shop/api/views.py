from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    OrderSerializer,
    PaymentSerializer,
    CartItemSerializer,
    CartDetailsSerializer,
    OrderStatusHistorySerializer
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
