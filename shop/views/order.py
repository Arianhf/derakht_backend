# shop/views/order.py

from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from ..models import Order, PaymentInfo
from ..serializers.order import OrderSerializer, OrderDetailSerializer


class OrderPagination(PageNumberPagination):
    """
    Pagination class for order listings
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for orders
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer
    pagination_class = OrderPagination

    def get_queryset(self):
        # Optimize queries to prevent N+1 issues
        return (
            Order.objects.filter(user=self.request.user)
            .select_related(
                "shipping_info",
                "payment_info",
            )
            .prefetch_related(
                "items",
                "items__product",
                "items__product__category",
                "items__product__images",
            )
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return OrderDetailSerializer
        return OrderSerializer

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """
        Cancel order
        """
        order = self.get_object()

        # Check if order can be canceled
        if order.status not in ["pending", "processing"]:
            return Response(
                {"error": "This order cannot be canceled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update order status
        order.status = "canceled"
        order.save()

        serializer = OrderSerializer(order)
        return Response(
            {
                "success": True,
                "message": "Order canceled successfully",
                "order": serializer.data,
            }
        )

    @action(detail=True, methods=["post"])
    def request_payment(self, request, pk=None):
        """
        Request payment for order
        """
        order = self.get_object()

        # Check if order is in pending status
        if order.status != "pending":
            return Response(
                {"error": "Payment can only be requested for pending orders"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # This would typically integrate with a payment gateway service
        # For demonstration purposes, we'll create a simple payment info record

        payment_info, created = PaymentInfo.objects.get_or_create(
            order=order, defaults={"method": "online", "status": "pending"}
        )

        # In a real implementation, you would get a payment URL from your payment gateway
        payment_url = f"https://payment-gateway.example.com/pay/{order.id}"
        transaction_id = f"TXN{int(timezone.now().timestamp())}"

        return Response(
            {
                "success": True,
                "payment_url": payment_url,
                "order_id": str(order.id),
                "amount": order.total_amount,
                "transaction_id": transaction_id,
            }
        )

    @action(detail=True, methods=["post"])
    def verify_payment(self, request, pk=None):
        """
        Verify payment for order
        """
        order = self.get_object()
        transaction_id = request.data.get("transaction_id")

        if not transaction_id:
            return Response(
                {"error": "Transaction ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get or create payment info
        payment_info, created = PaymentInfo.objects.get_or_create(
            order=order, defaults={"method": "online"}
        )

        # In a real implementation, you would verify the transaction with your payment gateway
        # For demonstration purposes, we'll assume the payment is successful

        # Update payment info
        payment_info.transaction_id = transaction_id
        payment_info.payment_date = timezone.now()
        payment_info.status = "completed"
        payment_info.save()

        # Update order status
        order.status = "confirmed"
        order.save()

        return Response(
            {
                "success": True,
                "message": "Payment verified successfully",
                "order": {
                    "id": str(order.id),
                    "status": order.status,
                    "total_amount": order.total_amount,
                    "payment_info": {
                        "method": payment_info.method,
                        "transaction_id": payment_info.transaction_id,
                        "payment_date": payment_info.payment_date,
                        "status": payment_info.status,
                    },
                },
            }
        )
