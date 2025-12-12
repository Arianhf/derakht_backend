"""
Integration tests for Cart API endpoints.
Tests cart operations for both authenticated and anonymous users.

Priority: P1 - Core user experience
"""

import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status

from shop.models import Cart, CartItem
from shop.tests.factories import ProductFactory, CartFactory, create_cart_with_items


@pytest.mark.integration
@pytest.mark.cart
class TestCartDetails:
    """Test retrieving cart details."""

    def test_get_cart_details_authenticated(self, authenticated_client, cart_with_items):
        """Test authenticated user can view their cart."""
        url = reverse("cart-details")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "items" in response.data
        assert "total_amount" in response.data
        assert len(response.data["items"]) == 2  # cart_with_items has 2 items

    def test_get_cart_details_anonymous(self, anonymous_cart_client):
        """Test anonymous user can view cart with anonymous ID."""
        # Create anonymous cart
        cart = CartFactory(anonymous=True)
        cart.anonymous_id = anonymous_cart_client.anonymous_id
        cart.save()

        ProductFactory(stock=10)

        url = reverse("cart-details")
        response = anonymous_cart_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_get_empty_cart(self, authenticated_client):
        """Test retrieving empty cart."""
        url = reverse("cart-details")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_amount"] == "0.00"
        assert len(response.data["items"]) == 0


@pytest.mark.integration
@pytest.mark.cart
class TestAddToCart:
    """Test adding products to cart."""

    def test_add_product_to_cart_authenticated(self, authenticated_client, product):
        """Test adding product to cart for authenticated user."""
        url = reverse("cart-add-item")
        response = authenticated_client.post(
            url, {"product_id": product.id, "quantity": 2}
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify cart item created
        user = authenticated_client.user
        assert Cart.objects.filter(user=user).exists()
        cart = Cart.objects.get(user=user)
        assert CartItem.objects.filter(cart=cart, product=product).exists()
        cart_item = CartItem.objects.get(cart=cart, product=product)
        assert cart_item.quantity == 2

    def test_add_product_to_cart_anonymous(self, anonymous_cart_client, product):
        """Test adding product to cart for anonymous user."""
        url = reverse("cart-add-item")
        response = anonymous_cart_client.post(
            url, {"product_id": product.id, "quantity": 1}
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify anonymous cart created
        cart = Cart.objects.get(anonymous_id=anonymous_cart_client.anonymous_id)
        assert CartItem.objects.filter(cart=cart, product=product).exists()

    def test_add_product_increases_quantity_if_exists(
        self, authenticated_client, cart_with_items
    ):
        """Test adding existing product increases quantity."""
        # Get first product from cart
        cart_item = cart_with_items.items.first()
        original_quantity = cart_item.quantity

        url = reverse("cart-add-item")
        response = authenticated_client.post(
            url, {"product_id": cart_item.product.id, "quantity": 2}
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify quantity increased
        cart_item.refresh_from_db()
        assert cart_item.quantity == original_quantity + 2

    def test_add_out_of_stock_product(self, authenticated_client, out_of_stock_product):
        """Test adding out-of-stock product fails."""
        url = reverse("cart-add-item")
        response = authenticated_client.post(
            url, {"product_id": out_of_stock_product.id, "quantity": 1}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "stock" in str(response.data).lower()

    def test_add_quantity_exceeding_stock(self, authenticated_client, product):
        """Test adding quantity exceeding available stock fails."""
        product.stock = 5
        product.save()

        url = reverse("cart-add-item")
        response = authenticated_client.post(
            url, {"product_id": product.id, "quantity": 10}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_product_with_zero_quantity(self, authenticated_client, product):
        """Test adding product with zero quantity fails."""
        url = reverse("cart-add-item")
        response = authenticated_client.post(
            url, {"product_id": product.id, "quantity": 0}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_nonexistent_product(self, authenticated_client):
        """Test adding non-existent product fails."""
        url = reverse("cart-add-item")
        response = authenticated_client.post(
            url, {"product_id": 99999, "quantity": 1}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.integration
@pytest.mark.cart
class TestUpdateCartQuantity:
    """Test updating cart item quantities."""

    def test_update_cart_item_quantity(self, authenticated_client, cart_with_items):
        """Test updating cart item quantity."""
        cart_item = cart_with_items.items.first()

        url = reverse("cart-update-quantity")
        response = authenticated_client.post(
            url, {"product_id": cart_item.product.id, "quantity": 5}
        )

        assert response.status_code == status.HTTP_200_OK

        cart_item.refresh_from_db()
        assert cart_item.quantity == 5

    def test_update_quantity_to_zero_removes_item(
        self, authenticated_client, cart_with_items
    ):
        """Test updating quantity to zero removes the item."""
        cart_item = cart_with_items.items.first()
        product_id = cart_item.product.id

        url = reverse("cart-update-quantity")
        response = authenticated_client.post(
            url, {"product_id": product_id, "quantity": 0}
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify item removed
        assert not CartItem.objects.filter(
            cart=cart_with_items, product_id=product_id
        ).exists()

    def test_update_quantity_exceeding_stock(self, authenticated_client, cart_with_items):
        """Test updating quantity beyond available stock fails."""
        cart_item = cart_with_items.items.first()
        cart_item.product.stock = 3
        cart_item.product.save()

        url = reverse("cart-update-quantity")
        response = authenticated_client.post(
            url, {"product_id": cart_item.product.id, "quantity": 10}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
@pytest.mark.cart
class TestRemoveFromCart:
    """Test removing items from cart."""

    def test_remove_cart_item(self, authenticated_client, cart_with_items):
        """Test removing item from cart."""
        cart_item = cart_with_items.items.first()
        product_id = cart_item.product.id

        url = reverse("cart-remove-item")
        response = authenticated_client.post(url, {"product_id": product_id})

        assert response.status_code == status.HTTP_200_OK

        # Verify item removed
        assert not CartItem.objects.filter(
            cart=cart_with_items, product_id=product_id
        ).exists()

    def test_remove_nonexistent_item(self, authenticated_client, cart_with_items):
        """Test removing non-existent item from cart."""
        url = reverse("cart-remove-item")
        response = authenticated_client.post(url, {"product_id": 99999})

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.integration
@pytest.mark.cart
class TestClearCart:
    """Test clearing entire cart."""

    def test_clear_cart(self, authenticated_client, cart_with_items):
        """Test clearing all items from cart."""
        url = reverse("cart-clear")
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK

        # Verify all items removed
        cart_with_items.refresh_from_db()
        assert cart_with_items.items.count() == 0

    def test_clear_empty_cart(self, authenticated_client):
        """Test clearing already empty cart."""
        url = reverse("cart-clear")
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
@pytest.mark.cart
class TestCartMerge:
    """Test merging anonymous cart with user cart on login."""

    def test_merge_anonymous_cart_on_login(self, api_client, user):
        """Test anonymous cart items are merged when user logs in."""
        # Create anonymous cart with items
        anonymous_cart = create_cart_with_items(anonymous=True, item_count=2)
        anonymous_id = anonymous_cart.anonymous_id

        # Login
        url = reverse("user-login")
        response = api_client.post(
            url, {"email": user.email, "password": "testpass123"}
        )

        assert response.status_code == status.HTTP_200_OK

        # Call merge endpoint
        access_token = response.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        merge_url = reverse("cart-merge")
        response = api_client.post(merge_url, {"anonymous_id": anonymous_id})

        assert response.status_code == status.HTTP_200_OK

        # Verify items merged to user cart
        user_cart = Cart.objects.get(user=user)
        assert user_cart.items.count() == 2

        # Verify anonymous cart no longer exists or is inactive
        anonymous_cart.refresh_from_db()
        assert anonymous_cart.is_active is False

    def test_merge_with_existing_user_cart(self, authenticated_client):
        """Test merging anonymous cart when user already has items."""
        user = authenticated_client.user

        # Create user cart with 1 item
        user_cart = create_cart_with_items(user=user, item_count=1)
        user_product = user_cart.items.first().product

        # Create anonymous cart with 2 items
        anonymous_cart = create_cart_with_items(anonymous=True, item_count=2)
        anonymous_id = anonymous_cart.anonymous_id

        # Merge
        url = reverse("cart-merge")
        response = authenticated_client.post(url, {"anonymous_id": anonymous_id})

        assert response.status_code == status.HTTP_200_OK

        # Verify user cart now has 3 items
        user_cart.refresh_from_db()
        assert user_cart.items.count() == 3


@pytest.mark.integration
@pytest.mark.cart
class TestPromoCodeApplication:
    """Test applying promo codes to cart."""

    def test_apply_promo_code(self, authenticated_client, cart_with_items, active_promo_code):
        """Test applying valid promo code to cart."""
        url = reverse("cart-apply-promo")
        response = authenticated_client.post(url, {"code": active_promo_code.code})

        assert response.status_code == status.HTTP_200_OK
        assert "discount" in response.data

        # Verify promo code stored in cart/order
        cart = Cart.objects.get(user=authenticated_client.user)
        # This depends on your implementation - promo might be on order, not cart

    def test_apply_invalid_promo_code(self, authenticated_client, cart_with_items):
        """Test applying invalid promo code fails."""
        url = reverse("cart-apply-promo")
        response = authenticated_client.post(url, {"code": "INVALID123"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_apply_expired_promo_code(
        self, authenticated_client, cart_with_items, expired_promo_code
    ):
        """Test applying expired promo code fails."""
        url = reverse("cart-apply-promo")
        response = authenticated_client.post(url, {"code": expired_promo_code.code})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "expired" in str(response.data).lower()

    def test_promo_code_percentage_discount(
        self, authenticated_client, cart_with_items, active_promo_code
    ):
        """Test percentage-based promo code calculates discount correctly."""
        # active_promo_code is 10% discount
        cart = cart_with_items
        original_total = cart.total_amount

        url = reverse("cart-apply-promo")
        response = authenticated_client.post(url, {"code": active_promo_code.code})

        assert response.status_code == status.HTTP_200_OK

        expected_discount = original_total * (active_promo_code.discount_value / 100)
        assert Decimal(response.data["discount"]) == expected_discount

    def test_promo_code_fixed_discount(
        self, authenticated_client, cart_with_items, fixed_promo_code
    ):
        """Test fixed-amount promo code."""
        url = reverse("cart-apply-promo")
        response = authenticated_client.post(url, {"code": fixed_promo_code.code})

        assert response.status_code == status.HTTP_200_OK
        assert Decimal(response.data["discount"]) == fixed_promo_code.discount_value


@pytest.mark.integration
@pytest.mark.cart
class TestCheckout:
    """Test checkout process."""

    def test_checkout_creates_order(self, authenticated_client, cart_with_items, user_with_addresses):
        """Test checkout converts cart to order."""
        # Use user with addresses
        authenticated_client.user = user_with_addresses
        cart_with_items.user = user_with_addresses
        cart_with_items.save()

        default_address = user_with_addresses.addresses.filter(is_default=True).first()

        url = reverse("cart-checkout")
        response = authenticated_client.post(
            url,
            {
                "address_id": default_address.id,
                "payment_method": "ONLINE",
            },
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        assert "order_id" in response.data

        # Verify order created
        from shop.models import Order

        order = Order.objects.get(id=response.data["order_id"])
        assert order.user == user_with_addresses
        assert order.items.count() == cart_with_items.items.count()

        # Verify cart is cleared
        cart_with_items.refresh_from_db()
        assert cart_with_items.items.count() == 0 or cart_with_items.is_active is False

    def test_checkout_empty_cart(self, authenticated_client):
        """Test checkout fails with empty cart."""
        url = reverse("cart-checkout")
        response = authenticated_client.post(
            url, {"payment_method": "ONLINE"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_checkout_validates_stock(self, authenticated_client, cart_with_items):
        """Test checkout fails if product is out of stock."""
        # Set product stock to 0
        cart_item = cart_with_items.items.first()
        cart_item.product.stock = 0
        cart_item.product.save()

        url = reverse("cart-checkout")
        response = authenticated_client.post(
            url, {"payment_method": "ONLINE"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "stock" in str(response.data).lower()
