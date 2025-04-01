# shop/views/payment.py

from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from ..models import Order, Payment
from ..services.payment import PaymentService


class PaymentRequestView(APIView):
    """
    API view to initiate a payment request
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id=None):
        """
        Initiate payment for an order
        """
        # Get the order
        order = get_object_or_404(Order, id=order_id, user=request.user)

        # Check if order is in pending status
        if order.status != "PENDING":
            return Response(
                {"error": "Payment can only be requested for pending orders"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the gateway name from request data
        gateway_name = request.data.get("gateway")

        # Request payment
        result = PaymentService.request_payment(order, gateway_name)

        if result["success"]:
            # Return payment URL and info
            return Response(
                {
                    "success": True,
                    "payment_url": result["payment_url"],
                    "authority": result.get("authority"),
                    "payment_id": result["payment_id"],
                    "gateway": result["gateway"],
                }
            )
        else:
            # Return error info
            return Response(
                {
                    "success": False,
                    "error": result.get("error_message", "Payment request failed"),
                    "gateway": result.get("gateway"),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


@method_decorator(csrf_exempt, name="dispatch")
class PaymentCallbackView(APIView):
    """
    API view to handle payment gateway callbacks
    """

    permission_classes = []  # Allow unauthenticated access for callbacks

    def get(self, request, gateway, payment_id):
        """
        Handle callback from payment gateway
        """
        # Get the payment
        payment = get_object_or_404(Payment, id=payment_id)

        # Verify payment
        result = PaymentService.verify_payment(payment, request.GET.dict(), gateway)

        # Get the frontend URL from settings or use a default
        from django.conf import settings

        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")

        # Create appropriate redirect URL
        if result["success"]:
            redirect_url = f"{frontend_url}/shop/checkout?transaction_id={result.get('ref_id', '')}&order_id={payment.order.id}&status=success"
        else:
            error_message = result.get("message", "Payment verification failed")
            redirect_url = f"{frontend_url}/shop/checkout?error={error_message}&order_id={payment.order.id}&status=failed"

        # Redirect to frontend
        return HttpResponseRedirect(redirect_url)

    def post(self, request, gateway, payment_id):
        """
        Handle callback from payment gateway (POST method)
        """
        # Some payment gateways use POST for callbacks
        # Get the payment
        payment = get_object_or_404(Payment, id=payment_id)

        # Verify payment
        result = PaymentService.verify_payment(payment, request.data, gateway)

        # Get the frontend URL from settings or use a default
        from django.conf import settings

        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")

        # Create appropriate redirect URL
        if result["success"]:
            redirect_url = f"{frontend_url}/payment/success?ref_id={result.get('ref_id', '')}&order_id={payment.order.id}"
        else:
            error_message = result.get("message", "Payment verification failed")
            redirect_url = f"{frontend_url}/payment/failed?error={error_message}&order_id={payment.order.id}"

        # Redirect to frontend
        return HttpResponseRedirect(redirect_url)


class PaymentStatusView(APIView):
    """
    API view to check payment status
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id=None):
        """
        Get payment status
        """
        # Get the payment
        payment = get_object_or_404(Payment, id=payment_id)

        # Check if the payment belongs to the user
        if payment.order.user != request.user:
            return Response(
                {"error": "You don't have permission to view this payment"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Return payment status and details
        return Response(
            {
                "payment_id": str(payment.id),
                "order_id": str(payment.order.id),
                "status": payment.status,
                "amount": payment.amount,
                "currency": payment.currency,
                "transaction_id": payment.transaction_id,
                "gateway": payment.gateway,
                "created_at": payment.created_at,
                "updated_at": payment.updated_at,
            }
        )


class PaymentMethodsView(APIView):
    """
    API view to get available payment methods
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get available payment methods
        """
        # Get available payment methods from settings or hardcode them
        from django.conf import settings

        available_methods = getattr(
            settings,
            "AVAILABLE_PAYMENT_METHODS",
            [
                {
                    "id": "zarinpal",
                    "name": "Zarinpal",
                    "description": "Pay using Zarinpal",
                    "icon": "/static/img/payment/zarinpal.png",
                    "enabled": True,
                }
            ],
        )

        return Response({"methods": available_methods})


class PaymentVerificationView(APIView):
    """
    API view for frontend to verify payment status
    This is different from the callback endpoint and is called directly
    by the frontend when the user is redirected back from payment gateway
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Verify payment status based on frontend request

        Expects:
        - order_id: UUID of the order
        - transaction_id: Transaction ID from payment gateway
        """
        order_id = request.data.get("order_id")
        transaction_id = request.data.get("transaction_id")

        if not order_id or not transaction_id:
            return Response(
                {"error": "Order ID and transaction ID are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the order and verify it belongs to the user
        order = get_object_or_404(Order, id=order_id)
        if order.user != request.user:
            return Response(
                {"error": "You don't have permission to access this order"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get the most recent payment for this order
        try:
            payment = Payment.objects.filter(order=order).latest("created_at")
        except Payment.DoesNotExist:
            return Response(
                {"error": "No payment found for this order"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # If payment is already completed, return success
        if payment.status == "COMPLETED":
            return Response(
                {
                    "status": "success",
                    "message": "Payment was already verified and completed",
                    "order_id": str(order.id),
                    "transaction_id": payment.transaction_id,
                }
            )

        # Verify payment using the gateway
        verification_data = {
            "transaction_id": transaction_id,
            # Add any other data your frontend sends from the payment gateway
        }

        try:
            result = PaymentService.verify_payment(
                payment, verification_data, payment.gateway
            )

            if result["success"]:
                return Response(
                    {
                        "status": "success",
                        "message": "Payment verified successfully",
                        "order_id": str(order.id),
                        "transaction_id": result.get("ref_id", transaction_id),
                    }
                )
            else:
                return Response(
                    {
                        "status": "failed",
                        "message": result.get("message", "Payment verification failed"),
                        "order_id": str(order.id),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response(
                {"status": "error", "message": str(e), "order_id": str(order.id)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
