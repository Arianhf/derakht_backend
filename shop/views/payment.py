# shop/views/payment.py

import logging
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser

from core.logging_utils import (
    get_logger,
    log_user_action,
    log_analytics_event,
    log_api_error,
    log_security_event,
    get_client_ip,
    sanitize_payment_params,
)
from ..models import Order, Payment, PaymentTransaction
from ..services.payment import PaymentService
from ..serializers.payment import (
    PaymentReceiptUploadSerializer,
    PaymentVerificationSerializer,
    PaymentRequestSerializer,
)
from ..choices import PaymentStatus

# Initialize loggers
logger = get_logger("shop.payments")
audit_logger = get_logger("audit")


class PaymentRequestView(APIView):
    """
    API view to initiate a payment request
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id=None):
        """
        Initiate payment for an order
        """
        # Validate input data
        serializer = PaymentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        gateway_name = serializer.validated_data.get("gateway")

        # Get the order
        order = get_object_or_404(Order, id=order_id, user=request.user)

        logger.info(
            f"Payment request initiated for order {order.id}",
            extra={
                "extra_data": {
                    "order_id": str(order.id),
                    "order_amount": float(order.total_amount),
                    "user_id": request.user.id,
                    "ip_address": get_client_ip(request),
                }
            },
        )

        # Check if order is in pending status
        if order.status != "PENDING":
            logger.warning(
                f"Payment request rejected: order {order.id} not in PENDING status",
                extra={
                    "order_id": str(order.id),
                    "order_status": order.status,
                    "user_id": request.user.id,
                },
            )
            return Response(
                {"error": "Payment can only be requested for pending orders"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Request payment
            result = PaymentService.request_payment(order, gateway_name)

            if result["success"]:
                logger.info(
                    f"Payment request successful for order {order.id}",
                    extra={
                        "extra_data": {
                            "order_id": str(order.id),
                            "payment_id": str(result["payment_id"]),
                            "gateway": result["gateway"],
                            "authority": result.get("authority"),
                            "amount": float(order.total_amount),
                        }
                    },
                )

                log_user_action(
                    audit_logger,
                    "payment_requested",
                    user_id=request.user.id,
                    user_email=request.user.email,
                    extra_data={
                        "order_id": str(order.id),
                        "payment_id": str(result["payment_id"]),
                        "gateway": result["gateway"],
                        "amount": float(order.total_amount),
                    },
                )

                log_analytics_event(
                    "payment_requested",
                    "shop",
                    user_id=request.user.id,
                    properties={
                        "order_id": str(order.id),
                        "gateway": result["gateway"],
                        "amount": float(order.total_amount),
                    },
                )

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
                logger.error(
                    f"Payment request failed for order {order.id}: {result.get('error_message')}",
                    extra={
                        "extra_data": {
                            "order_id": str(order.id),
                            "gateway": result.get("gateway"),
                            "error_message": result.get("error_message"),
                            "error_code": result.get("error_code"),
                        }
                    },
                )

                # Return error info
                return Response(
                    {
                        "success": False,
                        "error": result.get("error_message", "Payment request failed"),
                        "gateway": result.get("gateway"),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            log_api_error(
                logger,
                e,
                request.path,
                request.method,
                user_id=request.user.id,
                request_data={"order_id": str(order.id), "gateway": gateway_name},
            )
            raise


@method_decorator(csrf_exempt, name="dispatch")
class PaymentCallbackView(APIView):
    """
    API view to handle payment gateway callbacks

    CSRF EXEMPT JUSTIFICATION:
    This endpoint is exempt from CSRF protection because:
    1. This is a callback endpoint for external payment gateways (e.g., Zarinpal)
    2. Requests originate from the payment gateway's servers, not from user browsers
    3. No browser cookies or session data are involved in the verification process

    SECURITY MEASURES:
    - Payment verification with gateway using authority token (request parameter)
    - Payment status validation to prevent duplicate processing
    - Payment amount validation to ensure it matches the order total
    - Comprehensive logging of all callback attempts with IP addresses
    - Payment ID validation (must exist in database)
    - Order status checks prevent replay attacks

    ADDITIONAL SECURITY CONSIDERATIONS:
    - Frontend redirects use read-only query parameters
    - No state changes occur without successful gateway verification
    - All callback attempts are logged to audit trail

    TODO: Consider adding gateway signature verification for additional security layer
    """

    permission_classes = [AllowAny]  # Allow unauthenticated callbacks from payment gateway

    def get(self, request, gateway, payment_id):
        """
        Handle callback from payment gateway
        """
        # Get the payment
        payment = get_object_or_404(Payment, id=payment_id)

        logger.info(
            f"Payment callback received (GET) for payment {payment.id}",
            extra={
                "extra_data": {
                    "payment_id": str(payment.id),
                    "order_id": str(payment.order.id),
                    "gateway": gateway,
                    "callback_params": sanitize_payment_params(request.GET.dict()),
                    "ip_address": get_client_ip(request),
                }
            },
        )

        try:
            # Verify payment
            result = PaymentService.verify_payment(payment, request.GET.dict(), gateway)

            # Get the frontend URL from settings or use a default
            from django.conf import settings

            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")

            # Create appropriate redirect URL
            if result["success"]:
                logger.info(
                    f"Payment verified successfully: {payment.id}",
                    extra={
                        "extra_data": {
                            "payment_id": str(payment.id),
                            "order_id": str(payment.order.id),
                            "gateway": gateway,
                            "ref_id": result.get("ref_id"),
                            "amount": float(payment.amount),
                        }
                    },
                )

                log_analytics_event(
                    "payment_completed",
                    "shop",
                    user_id=payment.order.user.id,
                    properties={
                        "payment_id": str(payment.id),
                        "order_id": str(payment.order.id),
                        "gateway": gateway,
                        "amount": float(payment.amount),
                    },
                )

                redirect_url = f"{frontend_url}/shop/checkout?transaction_id={result.get('ref_id', '')}&order_id={payment.order.id}&status=success"
            else:
                logger.error(
                    f"Payment verification failed: {payment.id} - {result.get('message')}",
                    extra={
                        "extra_data": {
                            "payment_id": str(payment.id),
                            "order_id": str(payment.order.id),
                            "gateway": gateway,
                            "error_message": result.get("message"),
                        }
                    },
                )

                error_message = result.get("message", "Payment verification failed")
                redirect_url = f"{frontend_url}/shop/checkout?error={error_message}&order_id={payment.order.id}&status=failed"

            # Redirect to frontend
            return HttpResponseRedirect(redirect_url)

        except Exception as e:
            logger.error(
                f"Payment callback error for payment {payment.id}: {str(e)}",
                extra={
                    "payment_id": str(payment.id),
                    "order_id": str(payment.order.id),
                    "gateway": gateway,
                },
                exc_info=True,
            )
            raise

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
        - authority: (optional) Authority code from payment gateway
        """
        # Validate input data
        serializer = PaymentVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data["order_id"]
        transaction_id = serializer.validated_data["transaction_id"]

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


class PaymentReceiptUploadView(APIView):
    """
    API view to upload payment receipt for manual verification
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """
        Upload payment receipt for an order

        Expects:
        - order_id: UUID of the order
        - payment_receipt: Image file of the payment receipt
        """
        serializer = PaymentReceiptUploadSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_id = serializer.validated_data["order_id"]
        payment_receipt = serializer.validated_data["payment_receipt"]

        # Get the order and verify it belongs to the user
        order = get_object_or_404(Order, id=order_id)
        if order.user != request.user:
            return Response(
                {"error": "You don't have permission to access this order"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get or create a payment for this order
        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={
                "amount": order.total_amount,
                "status": PaymentStatus.PENDING,
                "gateway": "MANUAL",  # Manual payment via receipt upload
                "currency": order.currency,
            },
        )

        # If payment already exists and is completed, return error
        if not created and payment.status == PaymentStatus.COMPLETED:
            return Response(
                {"error": "Payment for this order is already completed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create a payment transaction with the receipt
        transaction = PaymentTransaction.objects.create(
            payment=payment,
            amount=payment.amount,
            payment_receipt=payment_receipt,
            provider_status="PENDING_VERIFICATION",
        )

        # Update payment status to pending if it's not already
        if payment.status != PaymentStatus.PENDING:
            payment.status = PaymentStatus.PENDING
            payment.save()

        return Response(
            {
                "success": True,
                "message": "Payment receipt uploaded successfully. Your payment will be verified manually.",
                "payment_id": str(payment.id),
                "transaction_id": str(transaction.id),
                "order_id": str(order.id),
            },
            status=status.HTTP_201_CREATED,
        )
