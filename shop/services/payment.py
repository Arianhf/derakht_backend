# shop/services/payment.py

from typing import Dict, Any, Optional

from ..gateways.factory import PaymentGatewayFactory
from ..models import Order, Payment


class PaymentService:
    """Service for handling payments"""

    @classmethod
    def request_payment(
        cls, order: Order, gateway_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Request a payment for an order

        Args:
            order: The order to pay for
            gateway_name: The name of the payment gateway to use

        Returns:
            Dictionary with payment information and redirect URL
        """
        # Get the payment gateway
        gateway = PaymentGatewayFactory.get_gateway(gateway_name)

        # Request the payment
        return gateway.request_payment(order)

    @classmethod
    def verify_payment(
        cls, payment: Payment, request_data: Dict, gateway_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify a payment

        Args:
            payment: The payment to verify
            request_data: Data from the payment gateway callback
            gateway_name: The name of the payment gateway to use

        Returns:
            Dictionary with verification result
        """
        # If gateway_name is not provided, use the one from the payment
        if gateway_name is None:
            gateway_name = payment.gateway

        # Get the payment gateway
        gateway = PaymentGatewayFactory.get_gateway(gateway_name)

        # Verify the payment
        return gateway.verify_payment(payment, request_data)
