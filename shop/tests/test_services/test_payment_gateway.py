# shop/tests/test_services/test_payment_gateway.py

from django.test import TestCase, override_settings
from shop.gateways.factory import PaymentGatewayFactory
from shop.gateways.base import PaymentGateway
from shop.gateways.zarinpal_sdk import ZarinpalSDKGateway


class MockPaymentGateway(PaymentGateway):
    """Mock payment gateway for testing"""

    def request_payment(self, order):
        return {"status": "success", "url": "http://mock.com/pay"}

    def verify_payment(self, payment, request_data):
        return {"status": "success", "verified": True}


class PaymentGatewayFactoryTest(TestCase):
    """Test cases for PaymentGatewayFactory"""

    def test_get_gateway_zarinpal_sdk(self):
        """Test getting Zarinpal SDK gateway"""
        gateway = PaymentGatewayFactory.get_gateway("zarinpal_sdk")
        self.assertIsInstance(gateway, ZarinpalSDKGateway)

    @override_settings(DEFAULT_PAYMENT_GATEWAY="zarinpal_sdk")
    def test_get_gateway_default(self):
        """Test getting default gateway from settings"""
        gateway = PaymentGatewayFactory.get_gateway()
        self.assertIsInstance(gateway, ZarinpalSDKGateway)

    def test_get_gateway_invalid_name(self):
        """Test that invalid gateway name raises ValueError"""
        with self.assertRaises(ValueError) as context:
            PaymentGatewayFactory.get_gateway("invalid_gateway")

        self.assertIn("Payment gateway 'invalid_gateway' not found", str(context.exception))

    def test_register_custom_gateway(self):
        """Test registering a custom payment gateway"""
        # Register mock gateway
        PaymentGatewayFactory.register("mock", MockPaymentGateway)

        # Get the gateway
        gateway = PaymentGatewayFactory.get_gateway("mock")
        self.assertIsInstance(gateway, MockPaymentGateway)

        # Test that it works
        result = gateway.request_payment(None)
        self.assertEqual(result["status"], "success")

    def test_gateway_registry_contains_zarinpal(self):
        """Test that registry contains Zarinpal gateway by default"""
        self.assertIn("zarinpal_sdk", PaymentGatewayFactory._registry)
        self.assertEqual(
            PaymentGatewayFactory._registry["zarinpal_sdk"], ZarinpalSDKGateway
        )

    def test_multiple_gateway_instances(self):
        """Test that factory creates new instances each time"""
        gateway1 = PaymentGatewayFactory.get_gateway("zarinpal_sdk")
        gateway2 = PaymentGatewayFactory.get_gateway("zarinpal_sdk")

        # Should be different instances
        self.assertIsNot(gateway1, gateway2)
        # But same type
        self.assertEqual(type(gateway1), type(gateway2))
