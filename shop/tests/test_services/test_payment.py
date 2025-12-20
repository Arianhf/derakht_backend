# shop/tests/test_services/test_payment.py

from unittest.mock import patch, MagicMock
from django.test import TestCase
from decimal import Decimal

from core.tests.base import BaseTestCase
from shop.services.payment import PaymentService
from shop.tests.fixtures import ShopFixtures
from shop.choices import OrderStatus


class PaymentServiceTest(BaseTestCase):
    """Test cases for PaymentService with mocked Zarinpal gateway"""

    def setUp(self):
        """Set up test data"""
        super().setUp()
        self.user = self.create_user()
        self.product = ShopFixtures.create_product(
            title="Test Product",
            price=Decimal("100000"),
            stock=10,
            sku="TEST-001",
        )
        self.order = ShopFixtures.create_order(
            user=self.user, total_amount=150000, status=OrderStatus.PENDING
        )
        ShopFixtures.create_shipping_info(self.order)

    @patch("shop.gateways.factory.PaymentGatewayFactory.get_gateway")
    def test_request_payment_success(self, mock_get_gateway):
        """Test successful payment request"""
        # Mock the gateway
        mock_gateway = MagicMock()
        mock_gateway.request_payment.return_value = {
            "status": "success",
            "authority": "A00000000000000000000000000123456789",
            "url": "https://www.zarinpal.com/pg/StartPay/A00000000000000000000000000123456789",
        }
        mock_get_gateway.return_value = mock_gateway

        # Request payment
        result = PaymentService.request_payment(self.order)

        # Verify results
        self.assertEqual(result["status"], "success")
        self.assertIn("authority", result)
        self.assertIn("url", result)

        # Verify gateway was called correctly
        mock_get_gateway.assert_called_once_with(None)
        mock_gateway.request_payment.assert_called_once_with(self.order)

    @patch("shop.gateways.factory.PaymentGatewayFactory.get_gateway")
    def test_request_payment_with_specific_gateway(self, mock_get_gateway):
        """Test payment request with specific gateway"""
        mock_gateway = MagicMock()
        mock_gateway.request_payment.return_value = {
            "status": "success",
            "authority": "TEST123",
            "url": "https://example.com/pay",
        }
        mock_get_gateway.return_value = mock_gateway

        # Request payment with specific gateway
        result = PaymentService.request_payment(self.order, gateway_name="zarinpal_sdk")

        # Verify gateway was called with correct name
        mock_get_gateway.assert_called_once_with("zarinpal_sdk")
        mock_gateway.request_payment.assert_called_once_with(self.order)

    @patch("shop.gateways.factory.PaymentGatewayFactory.get_gateway")
    def test_request_payment_failure(self, mock_get_gateway):
        """Test payment request failure"""
        # Mock gateway to return failure
        mock_gateway = MagicMock()
        mock_gateway.request_payment.return_value = {
            "status": "error",
            "error_code": 100,
            "error_message": "Invalid merchant ID",
        }
        mock_get_gateway.return_value = mock_gateway

        # Request payment
        result = PaymentService.request_payment(self.order)

        # Verify error response
        self.assertEqual(result["status"], "error")
        self.assertIn("error_code", result)
        self.assertIn("error_message", result)

    @patch("shop.gateways.factory.PaymentGatewayFactory.get_gateway")
    def test_verify_payment_success(self, mock_get_gateway):
        """Test successful payment verification"""
        # Create a payment for the order
        payment = ShopFixtures.create_payment(self.order)

        # Mock the gateway
        mock_gateway = MagicMock()
        mock_gateway.verify_payment.return_value = {
            "status": "success",
            "verified": True,
            "ref_id": "123456789",
        }
        mock_get_gateway.return_value = mock_gateway

        # Verify payment
        request_data = {
            "Authority": "A00000000000000000000000000123456789",
            "Status": "OK",
        }
        result = PaymentService.verify_payment(payment, request_data)

        # Verify results
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["verified"])
        self.assertIn("ref_id", result)

        # Verify gateway was called correctly
        mock_gateway.verify_payment.assert_called_once_with(payment, request_data)

    @patch("shop.gateways.factory.PaymentGatewayFactory.get_gateway")
    def test_verify_payment_uses_payment_gateway(self, mock_get_gateway):
        """Test that verify_payment uses the gateway from payment if not specified"""
        # Create a payment with specific gateway
        payment = ShopFixtures.create_payment(self.order, gateway="zarinpal_sdk")

        # Mock the gateway
        mock_gateway = MagicMock()
        mock_gateway.verify_payment.return_value = {"status": "success"}
        mock_get_gateway.return_value = mock_gateway

        # Verify payment without specifying gateway
        request_data = {"Authority": "TEST123", "Status": "OK"}
        PaymentService.verify_payment(payment, request_data)

        # Verify gateway was called with payment's gateway
        mock_get_gateway.assert_called_once_with("zarinpal_sdk")

    @patch("shop.gateways.factory.PaymentGatewayFactory.get_gateway")
    def test_verify_payment_failure(self, mock_get_gateway):
        """Test payment verification failure"""
        payment = ShopFixtures.create_payment(self.order)

        # Mock gateway to return failure
        mock_gateway = MagicMock()
        mock_gateway.verify_payment.return_value = {
            "status": "error",
            "verified": False,
            "error_code": 101,
            "error_message": "Transaction not found",
        }
        mock_get_gateway.return_value = mock_gateway

        # Verify payment
        request_data = {"Authority": "INVALID", "Status": "NOK"}
        result = PaymentService.verify_payment(payment, request_data)

        # Verify error response
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["verified"])
        self.assertIn("error_code", result)

    @patch("shop.gateways.factory.PaymentGatewayFactory.get_gateway")
    def test_verify_payment_with_override_gateway(self, mock_get_gateway):
        """Test verify_payment with gateway override"""
        payment = ShopFixtures.create_payment(self.order, gateway="zarinpal_sdk")

        # Mock the gateway
        mock_gateway = MagicMock()
        mock_gateway.verify_payment.return_value = {"status": "success"}
        mock_get_gateway.return_value = mock_gateway

        # Verify payment with different gateway
        request_data = {"Authority": "TEST123", "Status": "OK"}
        PaymentService.verify_payment(payment, request_data, gateway_name="other_gateway")

        # Verify gateway was called with override name
        mock_get_gateway.assert_called_once_with("other_gateway")
