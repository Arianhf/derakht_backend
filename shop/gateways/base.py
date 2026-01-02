# shop/gateways/base.py

from abc import ABC, abstractmethod
from typing import Dict

from ..models import Payment, Order
from ..services.payment import PaymentRequestResult, PaymentVerificationResult


class PaymentGateway(ABC):
    """Abstract base class for payment gateway implementations"""

    @abstractmethod
    def request_payment(self, order: Order) -> PaymentRequestResult:
        """
        Request a payment from the payment gateway

        Args:
            order: The order to be paid

        Returns:
            PaymentRequestResult with payment information and redirect URL
        """
        pass

    @abstractmethod
    def verify_payment(self, payment: Payment, request_data: Dict) -> PaymentVerificationResult:
        """
        Verify a payment with the payment gateway

        Args:
            payment: The payment to verify
            request_data: Data from the payment gateway callback

        Returns:
            PaymentVerificationResult with verification details
        """
        pass

    @abstractmethod
    def get_payment_url(self, payment: Payment, token: str) -> str:
        """
        Get the URL to redirect the user to for payment

        Args:
            payment: The payment object
            token: The token or authority from the payment gateway

        Returns:
            Payment URL
        """
        pass
