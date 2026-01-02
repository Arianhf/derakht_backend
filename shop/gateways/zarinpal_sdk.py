# shop/gateways/zarinpal_sdk.py

from django.conf import settings
from django.urls import reverse
from typing import Dict, Any, Optional

from zarinpal import ZarinPal, Config

from .base import PaymentGateway
from ..models import Payment, PaymentTransaction, Order
from ..choices import PaymentStatus


class ZarinpalSDKGateway(PaymentGateway):
    """Zarinpal payment gateway implementation using the official SDK"""

    def __init__(self):
        # Get settings from Django settings with defaults
        self.merchant_id = getattr(
            settings, "ZARINPAL_MERCHANT_ID", "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
        )
        self.access_token = getattr(settings, "ZARINPAL_ACCESS_TOKEN", "")
        self.callback_url = getattr(
            settings, "ZARINPAL_CALLBACK_URL", "http://localhost:8000"
        )
        self.sandbox = getattr(settings, "ZARINPAL_SANDBOX", True)

        # Create the Config object
        config = Config(
            sandbox=self.sandbox,
            merchant_id=self.merchant_id,
            access_token=self.access_token,
        )

        # Initialize Zarinpal client
        self.client = ZarinPal(config)

    def request_payment(self, order: Order):
        """
        Request a payment from Zarinpal

        Args:
            order: The order to be paid

        Returns:
            PaymentRequestResult with payment information and redirect URL
        """
        # Create a payment record or get the existing one
        payment, created = Payment.objects.get_or_create(
            order=order,
            status=PaymentStatus.PENDING,
            defaults={
                "amount": order.total_amount,
                "currency": order.currency,
                "gateway": "zarinpal_sdk",
            },
        )

        # Build the callback URL
        callback_url = f"{self.callback_url}{reverse('shop:payment_callback', kwargs={'gateway': 'zarinpal_sdk', 'payment_id': payment.id})}"

        try:
            # Request payment using the SDK
            payment_data = {
                "amount": payment.amount,
                "description": f"Payment for order #{order.id}",
                "callback_url": callback_url,
                "metadata": {
                    "mobile": order.phone_number,
                    "email": order.user.email,
                    "order_id": str(order.id),
                },
            }

            # Log the transaction request
            transaction = PaymentTransaction.objects.create(
                payment=payment, amount=payment.amount, raw_request=payment_data
            )

            # Use the SDK to request payment
            response = self.client.payments.create(
                data={
                    "amount": payment_data["amount"],
                    "description": payment_data["description"],
                    "callback_url": payment_data["callback_url"],
                    "metadata": payment_data["metadata"],
                }
            )

            # Update transaction with response
            transaction.raw_response = response
            transaction.provider_status = str(response.get("code", ""))
            transaction.save()

            response_data = response["data"]
            # Check if the request was successful
            if response_data.get("code") == 100:
                # Update payment with authority
                payment.reference_id = response_data.get("authority")
                payment.status = PaymentStatus.PROCESSING
                payment.save()

                # Generate payment URL
                payment_url = self.get_payment_url(
                    payment, response_data.get("authority")
                )

                return {
                    "success": True,
                    "payment_id": payment.id,
                    "authority": response_data.get("authority"),
                    "payment_url": payment_url,
                    "gateway": "zarinpal_sdk",
                    "error_message": None,
                }
            else:
                # Handle error
                payment.status = PaymentStatus.FAILED
                payment.save()

                return {
                    "success": False,
                    "payment_id": payment.id,
                    "payment_url": "",
                    "gateway": "zarinpal_sdk",
                    "authority": None,
                    "error_message": response_data.get(
                        "message", "Payment request failed"
                    ),
                }

        except Exception as e:
            # Handle exception
            payment.status = PaymentStatus.FAILED
            payment.save()

            # Create failure transaction record
            PaymentTransaction.objects.create(
                payment=payment,
                amount=payment.amount,
                raw_request=payment_data if "payment_data" in locals() else {},
                raw_response={"error": str(e)},
            )

            return {
                "success": False,
                "payment_id": payment.id,
                "payment_url": "",
                "gateway": "zarinpal_sdk",
                "authority": None,
                "error_message": str(e),
            }

    def verify_payment(self, payment: Payment, request_data: Dict):
        """
        Verify a payment with Zarinpal

        Args:
            payment: The payment to verify
            request_data: Data from the payment gateway callback

        Returns:
            PaymentVerificationResult with verification details
        """
        authority = request_data.get("Authority", "")
        status = request_data.get("Status", "")

        # Check if the payment was canceled by user
        if status != "OK":
            payment.status = PaymentStatus.FAILED
            payment.save()

            return {
                "success": False,
                "reference_id": None,
                "status": "FAILED",
                "amount": payment.amount,
                "error_message": "Payment was canceled by user",
            }

        try:
            # Create verification request data
            verify_data = {"authority": authority, "amount": payment.amount}

            # Log the verification request
            transaction = PaymentTransaction.objects.create(
                payment=payment, amount=payment.amount, raw_request=verify_data
            )

            # Use the SDK to verify payment
            response = self.client.verifications.verify(
                data={"authority": authority, "amount": payment.amount}
            )

            # Update transaction with response
            transaction.raw_response = response
            response_data = response["data"]
            transaction.provider_status = str(response_data.get("code", ""))
            transaction.transaction_id = response_data.get("ref_id")
            transaction.save()

            # Check if verification was successful
            if response_data.get("code") == 100:
                # Update payment status
                payment.status = PaymentStatus.COMPLETED
                payment.transaction_id = response_data.get("ref_id")
                payment.save()

                # Update order status
                order = payment.order
                order.status = "CONFIRMED"  # Assuming you have this status in your OrderStatus class
                order.save()

                return {
                    "success": True,
                    "reference_id": str(response_data.get("ref_id")),
                    "status": "COMPLETED",
                    "amount": payment.amount,
                    "error_message": None,
                }
            else:
                # Handle verification failure
                payment.status = PaymentStatus.FAILED
                payment.save()

                return {
                    "success": False,
                    "reference_id": None,
                    "status": "FAILED",
                    "amount": payment.amount,
                    "error_message": response_data.get(
                        "message", "Payment verification failed"
                    ),
                }

        except Exception as e:
            # Handle exception
            payment.status = PaymentStatus.FAILED
            payment.save()

            # Create failure transaction record
            PaymentTransaction.objects.create(
                payment=payment,
                amount=payment.amount,
                raw_request={"authority": authority, "amount": payment.amount},
                raw_response={"error": str(e)},
            )

            return {
                "success": False,
                "reference_id": None,
                "status": "FAILED",
                "amount": payment.amount,
                "error_message": str(e),
            }

    def get_payment_url(self, payment: Payment, token: str) -> str:
        """
        Get the URL to redirect the user to for payment

        Args:
            payment: The payment object
            token: The authority from Zarinpal

        Returns:
            Payment URL
        """
        base_url = self.client.get_base_url()
        return f"{base_url}/pg/StartPay/{token}"
