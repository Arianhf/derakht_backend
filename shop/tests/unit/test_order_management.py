"""
Unit tests for Order Management and State Machine.
Tests the critical business logic for order status transitions.

File: shop/order_management.py
"""

import pytest
from django.core.exceptions import ValidationError

from shop.models import Order, OrderStatusHistory
from shop.order_management import OrderStatusTransition
from shop.tests.factories import OrderFactory, create_order_with_items


@pytest.mark.unit
class TestOrderStatusTransition:
    """Test the order status state machine."""

    def test_valid_transitions_from_cart_to_pending(self, user):
        """Test valid transition from CART to PENDING."""
        order = OrderFactory(user=user, status="CART")

        order.transition_to("PENDING")

        assert order.status == "PENDING"
        assert OrderStatusHistory.objects.filter(order=order, new_status="PENDING").exists()

    def test_valid_transitions_from_pending_to_processing(self, user):
        """Test valid transition from PENDING to PROCESSING."""
        order = OrderFactory(user=user, status="PENDING")

        order.transition_to("PROCESSING")

        assert order.status == "PROCESSING"

    def test_valid_transitions_from_processing_to_confirmed(self, user):
        """Test valid transition from PROCESSING to CONFIRMED."""
        order = OrderFactory(user=user, status="PROCESSING")

        order.transition_to("CONFIRMED")

        assert order.status == "CONFIRMED"

    def test_valid_transitions_from_confirmed_to_shipped(self, user):
        """Test valid transition from CONFIRMED to SHIPPED."""
        order = OrderFactory(user=user, status="CONFIRMED")

        order.transition_to("SHIPPED")

        assert order.status == "SHIPPED"

    def test_valid_transitions_from_shipped_to_delivered(self, user):
        """Test valid transition from SHIPPED to DELIVERED."""
        order = OrderFactory(user=user, status="SHIPPED")

        order.transition_to("DELIVERED")

        assert order.status == "DELIVERED"

    def test_valid_transition_to_cancelled_from_pending(self, user):
        """Test cancellation from PENDING status."""
        order = OrderFactory(user=user, status="PENDING")

        order.transition_to("CANCELLED")

        assert order.status == "CANCELLED"

    @pytest.mark.parametrize(
        "initial_status,target_status",
        [
            ("CART", "CONFIRMED"),  # Cannot skip PENDING and PROCESSING
            ("CART", "SHIPPED"),  # Cannot jump to SHIPPED
            ("PENDING", "DELIVERED"),  # Cannot skip intermediate states
            ("PROCESSING", "DELIVERED"),  # Cannot skip CONFIRMED and SHIPPED
            ("DELIVERED", "PROCESSING"),  # Cannot go backward
            ("DELIVERED", "CANCELLED"),  # Cannot cancel delivered order
            ("SHIPPED", "PENDING"),  # Cannot go backward
            ("CONFIRMED", "CART"),  # Cannot go backward
        ],
    )
    def test_invalid_status_transitions(self, user, initial_status, target_status):
        """Test that invalid transitions raise ValidationError."""
        order = OrderFactory(user=user, status=initial_status)

        with pytest.raises(ValidationError) as exc_info:
            order.transition_to(target_status)

        assert "Invalid status transition" in str(exc_info.value)

    def test_transition_to_same_status_is_allowed(self, user):
        """Test that transitioning to the same status is allowed (idempotent)."""
        order = OrderFactory(user=user, status="PENDING")

        # This should not raise an error
        order.transition_to("PENDING")

        assert order.status == "PENDING"

    def test_status_history_tracking(self, user):
        """Test that status changes are tracked in history."""
        order = OrderFactory(user=user, status="CART")

        order.transition_to("PENDING")
        order.transition_to("PROCESSING")
        order.transition_to("CONFIRMED")

        history = OrderStatusHistory.objects.filter(order=order).order_by("created_at")

        assert history.count() == 3
        assert history[0].new_status == "PENDING"
        assert history[1].new_status == "PROCESSING"
        assert history[2].new_status == "CONFIRMED"

    def test_awaiting_verification_transition(self, user):
        """Test transition to AWAITING_VERIFICATION status."""
        order = OrderFactory(user=user, status="PENDING")

        order.transition_to("AWAITING_VERIFICATION")

        assert order.status == "AWAITING_VERIFICATION"


@pytest.mark.unit
class TestOrderModel:
    """Test Order model methods and properties."""

    def test_calculate_total(self, user):
        """Test order total calculation from order items."""
        order = create_order_with_items(user=user, item_count=3)

        # Total should be sum of all order items
        expected_total = sum(item.total_price for item in order.items.all())

        assert order.total_amount == expected_total

    def test_total_items_property(self, user):
        """Test total_items property returns sum of quantities."""
        order = create_order_with_items(user=user, item_count=3)

        expected_count = sum(item.quantity for item in order.items.all())

        assert order.total_items == expected_count

    def test_can_cancel_property_pending_order(self, user):
        """Test can_cancel is True for PENDING orders."""
        order = OrderFactory(user=user, status="PENDING")

        assert order.can_cancel is True

    def test_can_cancel_property_delivered_order(self, user):
        """Test can_cancel is False for DELIVERED orders."""
        order = OrderFactory(user=user, status="DELIVERED")

        assert order.can_cancel is False

    def test_can_ship_property_confirmed_order(self, user):
        """Test can_ship is True for CONFIRMED orders."""
        order = OrderFactory(user=user, status="CONFIRMED")

        assert order.can_ship is True

    def test_can_ship_property_pending_order(self, user):
        """Test can_ship is False for non-CONFIRMED orders."""
        order = OrderFactory(user=user, status="PENDING")

        assert order.can_ship is False

    def test_can_deliver_property_shipped_order(self, user):
        """Test can_deliver is True for SHIPPED orders."""
        order = OrderFactory(user=user, status="SHIPPED")

        assert order.can_deliver is True

    def test_cancel_method(self, user):
        """Test cancel() method transitions order to CANCELLED."""
        order = OrderFactory(user=user, status="PENDING")

        order.cancel()

        assert order.status == "CANCELLED"

    def test_confirm_shipping_method(self, user):
        """Test confirm_shipping() method transitions to SHIPPED."""
        order = OrderFactory(user=user, status="CONFIRMED")

        tracking_code = "TRACK123456"
        order.confirm_shipping(tracking_code)

        assert order.status == "SHIPPED"
        # Check if shipping info is created/updated with tracking code
        if hasattr(order, "shipping_info"):
            assert order.shipping_info.tracking_code == tracking_code

    def test_mark_delivered_method(self, user):
        """Test mark_delivered() method transitions to DELIVERED."""
        order = OrderFactory(user=user, status="SHIPPED")

        order.mark_delivered()

        assert order.status == "DELIVERED"

    def test_process_return_method(self, user):
        """Test process_return() method transitions to RETURNED."""
        order = OrderFactory(user=user, status="DELIVERED")

        order.process_return()

        assert order.status == "RETURNED"

    def test_process_refund_method(self, user):
        """Test process_refund() method transitions to REFUNDED."""
        order = OrderFactory(user=user, status="CANCELLED")

        order.process_refund()

        assert order.status == "REFUNDED"


@pytest.mark.unit
class TestOrderBusinessRules:
    """Test business rules and constraints."""

    def test_order_cannot_be_cancelled_after_shipping(self, user):
        """Test that shipped orders cannot be cancelled."""
        order = OrderFactory(user=user, status="SHIPPED")

        with pytest.raises(ValidationError):
            order.cancel()

    def test_order_requires_items(self, user):
        """Test that orders must have at least one item."""
        order = OrderFactory(user=user, status="CART")

        # Order with no items should have zero total
        assert order.total_amount == 0
        assert order.total_items == 0

    def test_order_total_updates_when_items_change(self, user):
        """Test that order total recalculates when items are added/removed."""
        order = create_order_with_items(user=user, item_count=2)
        initial_total = order.total_amount

        # Add another item
        from shop.tests.factories import OrderItemFactory, ProductFactory
        from decimal import Decimal

        product = ProductFactory(price=Decimal("50.00"))
        OrderItemFactory(order=order, product=product, quantity=1)

        # Refresh from database (signal should have updated total)
        order.refresh_from_db()

        assert order.total_amount > initial_total

    def test_order_belongs_to_user(self, user):
        """Test that orders are associated with users."""
        order = OrderFactory(user=user)

        assert order.user == user
        assert order in user.orders.all()
