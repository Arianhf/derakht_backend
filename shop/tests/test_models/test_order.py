# shop/tests/test_models/test_order.py

from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal

from core.tests.base import BaseTestCase
from shop.tests.fixtures import ShopFixtures
from shop.choices import OrderStatus


class OrderStatusTransitionTest(BaseTestCase):
    """Test cases for Order status transitions"""

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

    def test_cart_to_pending_transition(self):
        """Test transition from CART to PENDING"""
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.CART, total_amount=100000
        )

        order.transition_to(OrderStatus.PENDING)
        self.assertEqual(order.status, OrderStatus.PENDING)

    def test_pending_to_processing_transition(self):
        """Test transition from PENDING to PROCESSING"""
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.PENDING, total_amount=100000
        )

        order.transition_to(OrderStatus.PROCESSING)
        self.assertEqual(order.status, OrderStatus.PROCESSING)

    def test_pending_to_awaiting_verification_transition(self):
        """Test transition from PENDING to AWAITING_VERIFICATION"""
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.PENDING, total_amount=100000
        )

        order.transition_to(OrderStatus.AWAITING_VERIFICATION)
        self.assertEqual(order.status, OrderStatus.AWAITING_VERIFICATION)

    def test_processing_to_confirmed_transition(self):
        """Test transition from PROCESSING to CONFIRMED"""
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.PROCESSING, total_amount=100000
        )

        order.transition_to(OrderStatus.CONFIRMED)
        self.assertEqual(order.status, OrderStatus.CONFIRMED)

    def test_confirmed_to_shipped_transition(self):
        """Test transition from CONFIRMED to SHIPPED"""
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.CONFIRMED, total_amount=100000
        )

        order.confirm_shipping("TRACK123456")
        self.assertEqual(order.status, OrderStatus.SHIPPED)
        self.assertEqual(order.tracking_code, "TRACK123456")

    def test_shipped_to_delivered_transition(self):
        """Test transition from SHIPPED to DELIVERED"""
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.SHIPPED, total_amount=100000
        )

        order.mark_delivered()
        self.assertEqual(order.status, OrderStatus.DELIVERED)

    def test_delivered_to_returned_transition(self):
        """Test transition from DELIVERED to RETURNED"""
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.DELIVERED, total_amount=100000
        )

        order.process_return()
        self.assertEqual(order.status, OrderStatus.RETURNED)

    def test_returned_to_refunded_transition(self):
        """Test transition from RETURNED to REFUNDED"""
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.RETURNED, total_amount=100000
        )

        order.process_refund()
        self.assertEqual(order.status, OrderStatus.REFUNDED)

    def test_cancel_order_from_pending(self):
        """Test cancelling order from PENDING status"""
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.PENDING, total_amount=100000
        )

        order.cancel()
        self.assertEqual(order.status, OrderStatus.CANCELLED)

    def test_cancel_order_from_confirmed(self):
        """Test cancelling order from CONFIRMED status"""
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.CONFIRMED, total_amount=100000
        )

        order.cancel()
        self.assertEqual(order.status, OrderStatus.CANCELLED)

    def test_invalid_transition_raises_error(self):
        """Test that invalid transitions raise ValidationError"""
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.CART, total_amount=100000
        )

        # Cannot go directly from CART to SHIPPED
        with self.assertRaises(ValidationError):
            order.transition_to(OrderStatus.SHIPPED)

    def test_cannot_transition_from_delivered_to_pending(self):
        """Test that delivered orders cannot go back to pending"""
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.DELIVERED, total_amount=100000
        )

        with self.assertRaises(ValidationError):
            order.transition_to(OrderStatus.PENDING)

    def test_cannot_transition_from_shipped_to_pending(self):
        """Test that shipped orders cannot go back to pending"""
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.SHIPPED, total_amount=100000
        )

        with self.assertRaises(ValidationError):
            order.transition_to(OrderStatus.PENDING)

    def test_confirm_shipping_requires_tracking_code(self):
        """Test that confirming shipping requires a tracking code"""
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.CONFIRMED, total_amount=100000
        )

        with self.assertRaises(ValidationError):
            order.confirm_shipping("")

    def test_can_cancel_property(self):
        """Test can_cancel property"""
        # PENDING order can be cancelled
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.PENDING, total_amount=100000
        )
        self.assertTrue(order.can_cancel)

        # DELIVERED order cannot be cancelled
        order.status = OrderStatus.DELIVERED
        order.save()
        self.assertFalse(order.can_cancel)

    def test_can_ship_property(self):
        """Test can_ship property"""
        # CONFIRMED order can be shipped
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.CONFIRMED, total_amount=100000
        )
        self.assertTrue(order.can_ship)

        # PENDING order cannot be shipped
        order.status = OrderStatus.PENDING
        order.save()
        self.assertFalse(order.can_ship)

    def test_can_deliver_property(self):
        """Test can_deliver property"""
        # SHIPPED order can be delivered
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.SHIPPED, total_amount=100000
        )
        self.assertTrue(order.can_deliver)

        # PENDING order cannot be delivered
        order.status = OrderStatus.PENDING
        order.save()
        self.assertFalse(order.can_deliver)

    def test_calculate_total(self):
        """Test order total calculation from items"""
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.PENDING, total_amount=0
        )

        # Add items
        product1 = ShopFixtures.create_product(price=Decimal("50000"), sku="PROD1")
        product2 = ShopFixtures.create_product(price=Decimal("30000"), sku="PROD2")

        ShopFixtures.create_order_item(order, product1, quantity=2)  # 100000
        ShopFixtures.create_order_item(order, product2, quantity=1)  # 30000

        total = order.calculate_total()
        self.assertEqual(total, 130000)
        self.assertEqual(order.total_amount, 130000)

    def test_total_items_property(self):
        """Test total_items property"""
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.PENDING, total_amount=100000
        )

        # Add items
        product1 = ShopFixtures.create_product(price=Decimal("50000"), sku="PROD1")
        product2 = ShopFixtures.create_product(price=Decimal("30000"), sku="PROD2")

        ShopFixtures.create_order_item(order, product1, quantity=2)
        ShopFixtures.create_order_item(order, product2, quantity=3)

        self.assertEqual(order.total_items, 5)

    def test_product_count(self):
        """Test product_count method"""
        order = ShopFixtures.create_order(
            user=self.user, status=OrderStatus.PENDING, total_amount=100000
        )

        # Add items (different products)
        product1 = ShopFixtures.create_product(price=Decimal("50000"), sku="PROD1")
        product2 = ShopFixtures.create_product(price=Decimal("30000"), sku="PROD2")

        ShopFixtures.create_order_item(order, product1, quantity=2)
        ShopFixtures.create_order_item(order, product2, quantity=3)

        # Should have 2 different products
        self.assertEqual(order.product_count(), 2)
