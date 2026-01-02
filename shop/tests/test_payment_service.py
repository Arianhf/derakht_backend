from django.test import TestCase
from django.contrib.auth import get_user_model
from shop.models import Order, Product, Category, OrderItem, Payment
from shop.services.payment import PaymentService
from shop.tests.mocks import MockPaymentGateway
from shop.choices import OrderStatus, PaymentStatus
from decimal import Decimal
from unittest.mock import patch

User = get_user_model()


class PaymentServiceTestCase(TestCase):
    """Tests for PaymentService"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            age=25,
        )

        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category',
        )

        self.product = Product.objects.create(
            title='Test Product',
            slug='test-product',
            price=Decimal('100.00'),
            category=self.category,
        )

        # Create test order
        self.order = Order.objects.create(
            user=self.user,
            status=OrderStatus.PENDING,
            total_amount=200,
            phone_number='09121234567',
        )

        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=Decimal('100.00'),
        )

    @patch('shop.services.payment.PaymentGatewayFactory.get_gateway')
    def test_request_payment_success(self, mock_get_gateway):
        """Test successful payment request"""
        mock_gateway = MockPaymentGateway()
        mock_get_gateway.return_value = mock_gateway

        result = PaymentService.request_payment(self.order)

        self.assertTrue(result['success'])
        self.assertIn('payment_url', result)
        self.assertIn('authority', result)
        self.assertEqual(result['payment_url'], mock_gateway.payment_url)
        self.assertEqual(result['authority'], mock_gateway.authority)

    @patch('shop.services.payment.PaymentGatewayFactory.get_gateway')
    def test_request_payment_failure(self, mock_get_gateway):
        """Test failed payment request"""
        mock_gateway = MockPaymentGateway()
        mock_gateway.should_succeed = False
        mock_get_gateway.return_value = mock_gateway

        result = PaymentService.request_payment(self.order)

        self.assertFalse(result['success'])
        self.assertIn('error_message', result)
        self.assertEqual(result['error_message'], 'Mock gateway error')

    @patch('shop.services.payment.PaymentGatewayFactory.get_gateway')
    def test_request_payment_with_specific_gateway(self, mock_get_gateway):
        """Test payment request with specific gateway name"""
        mock_gateway = MockPaymentGateway()
        mock_get_gateway.return_value = mock_gateway

        result = PaymentService.request_payment(self.order, gateway_name='mock')

        mock_get_gateway.assert_called_once_with('mock')
        self.assertTrue(result['success'])

    @patch('shop.services.payment.PaymentGatewayFactory.get_gateway')
    def test_verify_payment_success(self, mock_get_gateway):
        """Test successful payment verification"""
        mock_gateway = MockPaymentGateway()
        mock_get_gateway.return_value = mock_gateway

        # Create payment
        payment = Payment.objects.create(
            order=self.order,
            amount=self.order.total_amount,
            gateway='mock',
            status=PaymentStatus.PENDING,
        )

        request_data = {'authority': mock_gateway.authority}
        result = PaymentService.verify_payment(payment, request_data)

        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual(result['reference_id'], mock_gateway.reference_id)

    @patch('shop.services.payment.PaymentGatewayFactory.get_gateway')
    def test_verify_payment_failure(self, mock_get_gateway):
        """Test failed payment verification"""
        mock_gateway = MockPaymentGateway()
        mock_gateway.should_succeed = False
        mock_get_gateway.return_value = mock_gateway

        # Create payment
        payment = Payment.objects.create(
            order=self.order,
            amount=self.order.total_amount,
            gateway='mock',
            status=PaymentStatus.PENDING,
        )

        request_data = {'authority': 'invalid_authority'}
        result = PaymentService.verify_payment(payment, request_data)

        self.assertFalse(result['success'])
        self.assertIn('error_message', result)
        self.assertEqual(result['status'], 'FAILED')

    @patch('shop.services.payment.PaymentGatewayFactory.get_gateway')
    def test_verify_payment_uses_payment_gateway(self, mock_get_gateway):
        """Test that verify uses gateway from payment record"""
        mock_gateway = MockPaymentGateway()
        mock_get_gateway.return_value = mock_gateway

        # Create payment with specific gateway
        payment = Payment.objects.create(
            order=self.order,
            amount=self.order.total_amount,
            gateway='zarinpal',
            status=PaymentStatus.PENDING,
        )

        request_data = {'authority': mock_gateway.authority}
        result = PaymentService.verify_payment(payment, request_data)

        # Should use gateway from payment record
        mock_get_gateway.assert_called_once_with('zarinpal')

    @patch('shop.services.payment.PaymentGatewayFactory.get_gateway')
    def test_verify_payment_with_override_gateway(self, mock_get_gateway):
        """Test verify with explicit gateway name override"""
        mock_gateway = MockPaymentGateway()
        mock_get_gateway.return_value = mock_gateway

        # Create payment with different gateway
        payment = Payment.objects.create(
            order=self.order,
            amount=self.order.total_amount,
            gateway='zarinpal',
            status=PaymentStatus.PENDING,
        )

        request_data = {'authority': mock_gateway.authority}
        result = PaymentService.verify_payment(
            payment, request_data, gateway_name='mock'
        )

        # Should use explicitly provided gateway
        mock_get_gateway.assert_called_once_with('mock')
        self.assertTrue(result['success'])
