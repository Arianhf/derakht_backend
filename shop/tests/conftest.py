"""
Shop app-specific pytest fixtures.
"""

import pytest
import responses
from decimal import Decimal

from shop.tests.factories import (
    ProductFactory,
    CategoryFactory,
    CartFactory,
    CartItemFactory,
    OrderFactory,
    OrderItemFactory,
    PaymentFactory,
    PaymentTransactionFactory,
    PromoCodeFactory,
    create_cart_with_items,
    create_order_with_items,
    create_payment_flow,
)


# ============================================================================
# PRODUCT FIXTURES
# ============================================================================


@pytest.fixture
def category():
    """Create a single category."""
    return CategoryFactory()


@pytest.fixture
def product(category):
    """Create a single product with stock."""
    return ProductFactory(category=category, stock=10, price=Decimal("99.99"))


@pytest.fixture
def product_factory():
    """Returns the ProductFactory for creating custom products."""
    return ProductFactory


@pytest.fixture
def out_of_stock_product(category):
    """Create a product with zero stock."""
    return ProductFactory(category=category, stock=0)


# ============================================================================
# CART FIXTURES
# ============================================================================


@pytest.fixture
def cart(user):
    """Create an empty cart for authenticated user."""
    return CartFactory(user=user)


@pytest.fixture
def anonymous_cart():
    """Create an anonymous cart."""
    return CartFactory(anonymous=True)


@pytest.fixture
def cart_with_items(user):
    """Create a cart with 2 items."""
    return create_cart_with_items(user=user, item_count=2)


@pytest.fixture
def anonymous_cart_with_items():
    """Create an anonymous cart with items."""
    return create_cart_with_items(anonymous=True, item_count=2)


# ============================================================================
# ORDER FIXTURES
# ============================================================================


@pytest.fixture
def order(user):
    """Create an order with 3 items in PENDING status."""
    return create_order_with_items(user=user, item_count=3, status="PENDING")


@pytest.fixture
def order_factory():
    """Returns the OrderFactory for creating custom orders."""
    return OrderFactory


@pytest.fixture
def confirmed_order(user):
    """Create an order in CONFIRMED status."""
    return create_order_with_items(user=user, item_count=2, status="CONFIRMED")


@pytest.fixture
def delivered_order(user):
    """Create an order in DELIVERED status."""
    return create_order_with_items(user=user, item_count=1, status="DELIVERED")


# ============================================================================
# PAYMENT FIXTURES
# ============================================================================


@pytest.fixture
def payment(order):
    """Create a payment for an order."""
    return PaymentFactory(order=order, amount=order.total_amount)


@pytest.fixture
def payment_transaction(payment):
    """Create a payment transaction."""
    return PaymentTransactionFactory(payment=payment)


@pytest.fixture
def payment_flow(user):
    """Create a complete payment flow (order, payment, transaction)."""
    order = create_order_with_items(user=user, item_count=2)
    return create_payment_flow(order=order)


# ============================================================================
# PROMO CODE FIXTURES
# ============================================================================


@pytest.fixture
def active_promo_code():
    """Create an active percentage-based promo code."""
    return PromoCodeFactory(
        code="SAVE10",
        discount_type="PERCENTAGE",
        discount_value=Decimal("10.00"),
        is_active=True,
    )


@pytest.fixture
def fixed_promo_code():
    """Create a fixed amount promo code."""
    return PromoCodeFactory(
        code="FIXED50",
        discount_type="FIXED",
        discount_value=Decimal("50000.00"),
        is_active=True,
    )


@pytest.fixture
def expired_promo_code():
    """Create an expired promo code."""
    from django.utils import timezone
    from datetime import timedelta

    return PromoCodeFactory(
        code="EXPIRED",
        valid_until=timezone.now() - timedelta(days=1),
        is_active=True,
    )


# ============================================================================
# ZARINPAL MOCK FIXTURES
# ============================================================================


@pytest.fixture
def mock_zarinpal_success():
    """
    Mock successful Zarinpal payment request and verification.
    Use with @responses.activate decorator.
    """

    def setup_mock():
        # Mock payment request
        responses.add(
            responses.POST,
            "https://payment.zarinpal.com/pg/v4/payment/request.json",
            json={
                "data": {"authority": "A00000000000000000000000000123456"},
                "errors": [],
            },
            status=200,
        )

        # Mock payment verification
        responses.add(
            responses.POST,
            "https://payment.zarinpal.com/pg/v4/payment/verify.json",
            json={
                "data": {
                    "ref_id": "12345678",
                    "status": "success",
                    "card_pan": "123456******1234",
                },
                "errors": [],
            },
            status=200,
        )

    return setup_mock


@pytest.fixture
def mock_zarinpal_failure():
    """
    Mock failed Zarinpal payment verification.
    """

    def setup_mock():
        responses.add(
            responses.POST,
            "https://payment.zarinpal.com/pg/v4/payment/verify.json",
            json={"data": {}, "errors": ["Invalid payment"]},
            status=400,
        )

    return setup_mock
