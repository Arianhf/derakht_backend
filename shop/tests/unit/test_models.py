"""
Unit tests for Shop models.
Tests model methods, properties, and business logic.
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from shop.models import Product, Category, Cart, CartItem, PromoCode
from shop.tests.factories import (
    ProductFactory,
    CategoryFactory,
    CartFactory,
    CartItemFactory,
    PromoCodeFactory,
    create_cart_with_items,
)


@pytest.mark.unit
class TestProductModel:
    """Test Product model methods and properties."""

    def test_product_creation(self):
        """Test basic product creation."""
        product = ProductFactory(
            title="Test Product",
            price=Decimal("99.99"),
            stock=10
        )

        assert product.title == "Test Product"
        assert product.price == Decimal("99.99")
        assert product.stock == 10
        assert product.is_active is True

    def test_product_slug_uniqueness(self):
        """Test that product slugs are unique."""
        ProductFactory(slug="test-product")

        with pytest.raises(IntegrityError):
            ProductFactory(slug="test-product")

    def test_product_is_in_stock(self):
        """Test is_in_stock property."""
        # Product with stock
        product = ProductFactory(stock=10)
        assert product.is_in_stock() is True

        # Product with zero stock
        product = ProductFactory(stock=0)
        assert product.is_in_stock() is False

    def test_product_age_range_property(self):
        """Test age_range property formatting."""
        product = ProductFactory(age_min=3, age_max=10)

        assert product.age_range == "3-10"

    def test_product_age_range_validation(self):
        """Test that age_max must be greater than age_min."""
        with pytest.raises(ValidationError):
            product = ProductFactory(age_min=10, age_max=5)
            product.full_clean()

    def test_product_feature_image(self):
        """Test feature_image property returns featured image."""
        product = ProductFactory()
        # Create multiple images, one featured
        from shop.tests.factories import ProductImageFactory
        image1 = ProductImageFactory(product=product, is_featured=False)
        image2 = ProductImageFactory(product=product, is_featured=True)

        assert product.feature_image == image2

    def test_product_str_representation(self):
        """Test string representation of product."""
        product = ProductFactory(title="Test Product")

        assert str(product) == "Test Product"

    def test_product_price_must_be_positive(self):
        """Test that product price must be positive."""
        with pytest.raises(ValidationError):
            product = ProductFactory(price=Decimal("-10.00"))
            product.full_clean()

    def test_product_stock_cannot_be_negative(self):
        """Test that stock cannot be negative."""
        with pytest.raises(ValidationError):
            product = ProductFactory(stock=-5)
            product.full_clean()


@pytest.mark.unit
class TestCategoryModel:
    """Test Category model and hierarchical structure."""

    def test_category_creation(self):
        """Test basic category creation."""
        category = CategoryFactory(name="Electronics")

        assert category.name == "Electronics"
        assert category.parent is None

    def test_category_hierarchy(self):
        """Test parent-child category relationships."""
        parent = CategoryFactory(name="Electronics")
        child = CategoryFactory(name="Smartphones", parent=parent)

        assert child.parent == parent
        assert child in parent.children.all()

    def test_category_slug_generation(self):
        """Test category slug is generated from name."""
        category = CategoryFactory(name="Test Category")

        assert "test-category" in category.slug

    def test_category_str_representation(self):
        """Test category string representation."""
        category = CategoryFactory(name="Books")

        assert str(category) == "Books"


@pytest.mark.unit
class TestCartModel:
    """Test Cart model and cart operations."""

    def test_cart_creation_for_user(self, user):
        """Test cart creation for authenticated user."""
        cart = CartFactory(user=user)

        assert cart.user == user
        assert cart.anonymous_id is None

    def test_cart_creation_anonymous(self):
        """Test anonymous cart creation."""
        cart = CartFactory(anonymous=True)

        assert cart.user is None
        assert cart.anonymous_id is not None

    def test_cart_must_have_user_or_anonymous_id(self):
        """Test cart requires either user or anonymous_id."""
        with pytest.raises(ValidationError):
            cart = Cart(user=None, anonymous_id=None)
            cart.full_clean()

    def test_cart_total_amount_calculation(self):
        """Test cart total_amount property."""
        cart = create_cart_with_items(item_count=3)

        expected_total = sum(item.total_price for item in cart.items.all())
        assert cart.total_amount == expected_total

    def test_cart_items_count(self):
        """Test cart items_count property."""
        cart = create_cart_with_items(item_count=3)

        expected_count = sum(item.quantity for item in cart.items.all())
        assert cart.items_count == expected_count

    def test_empty_cart_total(self):
        """Test empty cart has zero total."""
        cart = CartFactory()

        assert cart.total_amount == Decimal("0.00")
        assert cart.items_count == 0


@pytest.mark.unit
class TestCartItemModel:
    """Test CartItem model."""

    def test_cart_item_creation(self, cart, product):
        """Test cart item creation."""
        cart_item = CartItemFactory(cart=cart, product=product, quantity=2)

        assert cart_item.cart == cart
        assert cart_item.product == product
        assert cart_item.quantity == 2

    def test_cart_item_price_property(self):
        """Test cart item price property."""
        product = ProductFactory(price=Decimal("99.99"))
        cart_item = CartItemFactory(product=product, quantity=1)

        assert cart_item.price == product.price

    def test_cart_item_total_price(self):
        """Test cart item total_price calculation."""
        product = ProductFactory(price=Decimal("50.00"))
        cart_item = CartItemFactory(product=product, quantity=3)

        assert cart_item.total_price == Decimal("150.00")

    def test_cart_item_quantity_must_be_positive(self):
        """Test cart item quantity must be positive."""
        with pytest.raises(ValidationError):
            cart_item = CartItemFactory(quantity=0)
            cart_item.full_clean()


@pytest.mark.unit
class TestPromoCodeModel:
    """Test PromoCode model and discount logic."""

    def test_promo_code_creation(self):
        """Test promo code creation."""
        promo = PromoCodeFactory(
            code="SAVE10",
            discount_type="PERCENTAGE",
            discount_value=Decimal("10.00")
        )

        assert promo.code == "SAVE10"
        assert promo.discount_type == "PERCENTAGE"

    def test_promo_code_is_valid(self):
        """Test promo code validity check."""
        promo = PromoCodeFactory(is_active=True)

        assert promo.is_valid() is True

    def test_promo_code_inactive(self):
        """Test inactive promo code."""
        promo = PromoCodeFactory(is_active=False)

        assert promo.is_valid() is False

    def test_promo_code_expired(self):
        """Test expired promo code."""
        from django.utils import timezone
        from datetime import timedelta

        promo = PromoCodeFactory(
            valid_until=timezone.now() - timedelta(days=1)
        )

        assert promo.is_valid() is False

    def test_promo_code_not_yet_valid(self):
        """Test promo code that hasn't started yet."""
        from django.utils import timezone
        from datetime import timedelta

        promo = PromoCodeFactory(
            valid_from=timezone.now() + timedelta(days=1)
        )

        assert promo.is_valid() is False

    def test_promo_code_usage_limit(self):
        """Test promo code with usage limit."""
        promo = PromoCodeFactory(usage_limit=5, times_used=5)

        assert promo.is_valid() is False

    def test_promo_code_percentage_discount(self):
        """Test percentage discount calculation."""
        promo = PromoCodeFactory(
            discount_type="PERCENTAGE",
            discount_value=Decimal("15.00")
        )
        order_total = Decimal("100.00")

        discount = promo.calculate_discount(order_total)

        assert discount == Decimal("15.00")

    def test_promo_code_fixed_discount(self):
        """Test fixed amount discount."""
        promo = PromoCodeFactory(
            discount_type="FIXED",
            discount_value=Decimal("50.00")
        )
        order_total = Decimal("200.00")

        discount = promo.calculate_discount(order_total)

        assert discount == Decimal("50.00")

    def test_promo_code_max_discount_cap(self):
        """Test maximum discount cap."""
        promo = PromoCodeFactory(
            discount_type="PERCENTAGE",
            discount_value=Decimal("50.00"),  # 50% off
            max_discount_amount=Decimal("100.00")  # Max 100
        )
        order_total = Decimal("500.00")  # Would be 250 discount

        discount = promo.calculate_discount(order_total)

        assert discount == Decimal("100.00")  # Capped at max

    def test_promo_code_minimum_purchase(self):
        """Test minimum purchase requirement."""
        promo = PromoCodeFactory(
            min_purchase_amount=Decimal("100.00")
        )

        # Below minimum
        assert promo.is_valid_for_amount(Decimal("50.00")) is False

        # At or above minimum
        assert promo.is_valid_for_amount(Decimal("100.00")) is True
        assert promo.is_valid_for_amount(Decimal("150.00")) is True
