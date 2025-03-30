# shop/gateways/factory.py

from django.conf import settings
from typing import Dict, Type

from .base import PaymentGateway
from .zarinpal_sdk import ZarinpalSDKGateway


class PaymentGatewayFactory:
    """Factory for creating payment gateway instances"""

    # Registry of available payment gateways
    _registry: Dict[str, Type[PaymentGateway]] = {
        "zarinpal_sdk": ZarinpalSDKGateway,
    }

    @classmethod
    def register(cls, name: str, gateway_class: Type[PaymentGateway]) -> None:
        """
        Register a new payment gateway

        Args:
            name: The name of the gateway
            gateway_class: The gateway class
        """
        cls._registry[name] = gateway_class

    @classmethod
    def get_gateway(cls, name: str = None) -> PaymentGateway:
        """
        Get a payment gateway instance

        Args:
            name: The name of the gateway, or None to use the default

        Returns:
            A payment gateway instance

        Raises:
            ValueError: If the gateway is not found
        """
        # If no name is provided, use the default from settings
        if name is None:
            name = getattr(settings, "DEFAULT_PAYMENT_GATEWAY", "zarinpal")

        # Get the gateway class
        gateway_class = cls._registry.get(name)
        if gateway_class is None:
            raise ValueError(f"Payment gateway '{name}' not found")

        # Create and return an instance
        return gateway_class()
