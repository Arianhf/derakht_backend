# shop/tests/test_views/test_cart.py

import uuid
from decimal import Decimal
from django.urls import reverse
from rest_framework import status

from core.tests.base import BaseAPITestCase
from shop.tests.fixtures import ShopFixtures
from shop.models import Cart, CartItem


class CartViewSetTest(BaseAPITestCase):
    """Test cases for CartViewSet API endpoints"""

    def setUp(self):
        """Set up test data"""
        super().setUp()
        self.product1 = ShopFixtures.create_product(
            title="Product 1",
            price=Decimal("100000"),
            stock=10,
            sku="PROD-001",
            slug="product-1",
        )
        self.product2 = ShopFixtures.create_product(
            title="Product 2",
            price=Decimal("50000"),
            stock=5,
            sku="PROD-002",
            slug="product-2",
        )

    def test_get_cart_details_authenticated_user(self):
        """Test getting cart details for authenticated user"""
        user = self.authenticate()
        cart = ShopFixtures.create_cart(user=user)
        ShopFixtures.create_cart_item(cart, self.product1, quantity=2)

        url = reverse("cart-details")
        response = self.client.get(url)

        self.assertSuccess(response)
        self.assertEqual(response.data["items_count"], 2)
        self.assertEqual(response.data["total_amount"], 200000)
        self.assertTrue(response.data["is_authenticated"])

    def test_get_cart_details_anonymous_user(self):
        """Test getting cart details for anonymous user"""
        # Create anonymous cart
        anonymous_id = uuid.uuid4()
        cart = ShopFixtures.create_cart(anonymous_id=anonymous_id)
        ShopFixtures.create_cart_item(cart, self.product1, quantity=1)

        url = reverse("cart-details")
        response = self.client.get(url, {"cart_id": str(anonymous_id)})

        self.assertSuccess(response)
        self.assertEqual(response.data["items_count"], 1)
        self.assertFalse(response.data["is_authenticated"])

    def test_add_item_to_cart_authenticated(self):
        """Test adding item to cart for authenticated user"""
        user = self.authenticate()

        url = reverse("cart-add-item")
        data = {"product_id": self.product1.id, "quantity": 2}
        response = self.client.post(url, data, format="json")

        self.assertSuccess(response)
        self.assertEqual(response.data["items_count"], 2)

        # Verify cart item was created
        cart = Cart.objects.get(user=user)
        cart_item = CartItem.objects.get(cart=cart, product=self.product1)
        self.assertEqual(cart_item.quantity, 2)

    def test_add_item_to_cart_anonymous(self):
        """Test adding item to cart for anonymous user"""
        url = reverse("cart-add-item")
        data = {"product_id": self.product1.id, "quantity": 1}
        response = self.client.post(url, data, format="json")

        self.assertSuccess(response)

        # Verify anonymous cart was created
        self.assertEqual(Cart.objects.filter(user=None).count(), 1)

    def test_add_item_exceeds_stock(self):
        """Test adding item quantity that exceeds available stock"""
        user = self.authenticate()

        url = reverse("cart-add-item")
        data = {"product_id": self.product1.id, "quantity": 20}  # Stock is only 10
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("error", response.data)

    def test_add_unavailable_product(self):
        """Test adding unavailable product to cart"""
        user = self.authenticate()
        unavailable_product = ShopFixtures.create_product(
            title="Unavailable Product",
            price=Decimal("50000"),
            stock=5,
            sku="UNAVAIL-001",
            slug="unavailable-1",
            is_available=False,
        )

        url = reverse("cart-add-item")
        data = {"product_id": unavailable_product.id, "quantity": 1}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_update_cart_item_quantity(self):
        """Test updating cart item quantity"""
        user = self.authenticate()
        cart = ShopFixtures.create_cart(user=user)
        ShopFixtures.create_cart_item(cart, self.product1, quantity=1)

        url = reverse("cart-update-quantity")
        data = {"product_id": self.product1.id, "quantity": 5}
        response = self.client.post(url, data, format="json")

        self.assertSuccess(response)

        # Verify quantity was updated
        cart_item = CartItem.objects.get(cart=cart, product=self.product1)
        self.assertEqual(cart_item.quantity, 5)

    def test_update_quantity_to_zero_removes_item(self):
        """Test that updating quantity to 0 removes the item"""
        user = self.authenticate()
        cart = ShopFixtures.create_cart(user=user)
        ShopFixtures.create_cart_item(cart, self.product1, quantity=2)

        url = reverse("cart-update-quantity")
        data = {"product_id": self.product1.id, "quantity": 0}
        response = self.client.post(url, data, format="json")

        self.assertSuccess(response)

        # Verify item was removed
        self.assertFalse(
            CartItem.objects.filter(cart=cart, product=self.product1).exists()
        )

    def test_remove_item_from_cart(self):
        """Test removing item from cart"""
        user = self.authenticate()
        cart = ShopFixtures.create_cart(user=user)
        ShopFixtures.create_cart_item(cart, self.product1, quantity=2)

        url = reverse("cart-remove-item")
        data = {"product_id": self.product1.id}
        response = self.client.post(url, data, format="json")

        self.assertSuccess(response)

        # Verify item was removed
        self.assertFalse(
            CartItem.objects.filter(cart=cart, product=self.product1).exists()
        )

    def test_clear_cart(self):
        """Test clearing all items from cart"""
        user = self.authenticate()
        cart = ShopFixtures.create_cart(user=user)
        ShopFixtures.create_cart_item(cart, self.product1, quantity=2)
        ShopFixtures.create_cart_item(cart, self.product2, quantity=1)

        url = reverse("cart-clear")
        response = self.client.post(url, {}, format="json")

        self.assertSuccess(response)

        # Verify all items were removed
        self.assertEqual(CartItem.objects.filter(cart=cart).count(), 0)

    def test_merge_anonymous_cart_with_user_cart(self):
        """Test merging anonymous cart with user cart upon login"""
        # Create anonymous cart
        anonymous_id = uuid.uuid4()
        anon_cart = ShopFixtures.create_cart(anonymous_id=anonymous_id)
        ShopFixtures.create_cart_item(anon_cart, self.product1, quantity=2)
        ShopFixtures.create_cart_item(anon_cart, self.product2, quantity=1)

        # Authenticate user
        user = self.authenticate()

        # Merge carts
        url = reverse("cart-merge")
        data = {"anonymous_cart_id": str(anonymous_id)}
        response = self.client.post(url, data, format="json")

        self.assertSuccess(response)

        # Verify items were merged to user cart
        user_cart = Cart.objects.get(user=user)
        self.assertEqual(CartItem.objects.filter(cart=user_cart).count(), 2)

        # Verify anonymous cart was deleted
        self.assertFalse(Cart.objects.filter(anonymous_id=anonymous_id).exists())

    def test_merge_cart_requires_authentication(self):
        """Test that merging cart requires authentication"""
        anonymous_id = uuid.uuid4()

        url = reverse("cart-merge")
        data = {"anonymous_cart_id": str(anonymous_id)}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_shipping_estimate(self):
        """Test getting shipping estimate"""
        user = self.authenticate()
        cart = ShopFixtures.create_cart(user=user)
        ShopFixtures.create_cart_item(cart, self.product1, quantity=2)

        url = reverse("cart-shipping-estimate")
        data = {"province": "تهران", "city": "تهران"}
        response = self.client.post(url, data, format="json")

        self.assertSuccess(response)
        self.assertIn("shipping_methods", response.data)
        self.assertIn("cart_total", response.data)

    def test_shipping_estimate_empty_cart(self):
        """Test shipping estimate with empty cart"""
        user = self.authenticate()
        ShopFixtures.create_cart(user=user)

        url = reverse("cart-shipping-estimate")
        data = {"province": "تهران", "city": "تهران"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_creates_order(self):
        """Test that checkout creates an order"""
        user = self.authenticate()
        cart = ShopFixtures.create_cart(user=user)
        ShopFixtures.create_cart_item(cart, self.product1, quantity=2)

        url = reverse("cart-checkout")
        data = {
            "shipping_info": {
                "recipient_name": "Test User",
                "address": "Test Address",
                "city": "تهران",
                "province": "تهران",
                "postal_code": "1234567890",
                "phone_number": "+989123456789",
            },
            "shipping_method_id": "standard_post",
        }
        response = self.client.post(url, data, format="json")

        self.assertSuccess(response)
        self.assertIn("id", response.data)

        # Verify cart was cleared
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 0)

    def test_checkout_empty_cart_fails(self):
        """Test that checkout with empty cart fails"""
        user = self.authenticate()
        ShopFixtures.create_cart(user=user)

        url = reverse("cart-checkout")
        data = {
            "shipping_info": {
                "recipient_name": "Test User",
                "address": "Test Address",
                "city": "تهران",
                "province": "تهران",
                "postal_code": "1234567890",
                "phone_number": "+989123456789",
            },
            "shipping_method_id": "standard_post",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_invalid_shipping_method(self):
        """Test checkout with invalid shipping method"""
        user = self.authenticate()
        cart = ShopFixtures.create_cart(user=user)
        ShopFixtures.create_cart_item(cart, self.product1, quantity=1)

        url = reverse("cart-checkout")
        data = {
            "shipping_info": {
                "recipient_name": "Test User",
                "address": "Test Address",
                "city": "اصفهان",
                "province": "اصفهان",
                "postal_code": "1234567890",
                "phone_number": "+989123456789",
            },
            "shipping_method_id": "express",  # Not available in Isfahan
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
