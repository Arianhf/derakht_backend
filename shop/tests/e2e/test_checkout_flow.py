"""
End-to-end tests for complete checkout flow.
Tests the entire user journey from browsing to payment.

Priority: P2 - Validates complete user workflows
"""

import pytest
import responses
from decimal import Decimal
from django.urls import reverse
from rest_framework import status

from shop.models import Order, Payment, Invoice
from shop.tests.factories import ProductFactory, PromoCodeFactory
from users.tests.factories import UserFactory, AddressFactory


@pytest.mark.e2e
class TestCompleteCheckoutFlow:
    """Test complete checkout flow from cart to payment."""

    @responses.activate
    def test_complete_purchase_flow_authenticated_user(self, api_client, mock_email_backend):
        """
        Test complete flow: Signup → Browse → Add to Cart → Checkout → Payment
        """
        # 1. USER SIGNUP
        signup_url = reverse("user-signup")
        signup_data = {
            "email": "customer@example.com",
            "password": "SecurePass123!",
            "name": "Test Customer",
            "phone_number": "+989123456789",
            "age": 30,
        }
        response = api_client.post(signup_url, signup_data)
        assert response.status_code == status.HTTP_201_CREATED
        access_token = response.data["access"]
        user_id = response.data["user"]["id"]

        # Authenticate client
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # 2. CREATE ADDRESS
        address_url = reverse("user-addresses-list")
        address_data = {
            "recipient_name": "Test Customer",
            "address": "123 Test Street",
            "city": "Tehran",
            "province": "Tehran",
            "postal_code": "1234567890",
            "phone_number": "+989123456789",
        }
        response = api_client.post(address_url, address_data)
        assert response.status_code == status.HTTP_201_CREATED
        address_id = response.data["id"]

        # 3. BROWSE PRODUCTS
        products_url = reverse("product-list")
        response = api_client.get(products_url)
        assert response.status_code == status.HTTP_200_OK

        # Create test products
        product1 = ProductFactory(
            title="Product 1",
            price=Decimal("100.00"),
            stock=10
        )
        product2 = ProductFactory(
            title="Product 2",
            price=Decimal("150.00"),
            stock=5
        )

        # 4. ADD PRODUCTS TO CART
        add_to_cart_url = reverse("cart-add-item")

        # Add product 1
        response = api_client.post(add_to_cart_url, {
            "product_id": product1.id,
            "quantity": 2
        })
        assert response.status_code == status.HTTP_200_OK

        # Add product 2
        response = api_client.post(add_to_cart_url, {
            "product_id": product2.id,
            "quantity": 1
        })
        assert response.status_code == status.HTTP_200_OK

        # 5. VIEW CART
        cart_url = reverse("cart-details")
        response = api_client.get(cart_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["items"]) == 2
        cart_total = Decimal(response.data["total_amount"])
        expected_total = (product1.price * 2) + product2.price
        assert cart_total == expected_total

        # 6. APPLY PROMO CODE
        promo = PromoCodeFactory(
            code="WELCOME10",
            discount_type="PERCENTAGE",
            discount_value=Decimal("10.00")
        )
        apply_promo_url = reverse("cart-apply-promo")
        response = api_client.post(apply_promo_url, {"code": "WELCOME10"})
        assert response.status_code == status.HTTP_200_OK

        # 7. CHECKOUT (CREATE ORDER)
        checkout_url = reverse("cart-checkout")
        response = api_client.post(checkout_url, {
            "address_id": address_id,
            "payment_method": "ONLINE",
        })
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        order_id = response.data["order_id"]

        # Verify order created
        order = Order.objects.get(id=order_id)
        assert order.user.id == user_id
        assert order.items.count() == 2
        assert order.status == "PENDING"

        # 8. REQUEST PAYMENT
        # Mock Zarinpal payment request
        responses.add(
            responses.POST,
            "https://payment.zarinpal.com/pg/v4/payment/request.json",
            json={
                "data": {"authority": "A00000000000000000000000000123456"},
                "errors": []
            },
            status=200
        )

        payment_request_url = reverse("payment-request", kwargs={"order_id": order_id})
        response = api_client.post(payment_request_url, {"gateway": "zarinpal"})
        assert response.status_code == status.HTTP_200_OK
        assert "payment_url" in response.data

        # Verify payment created
        payment = Payment.objects.get(order=order)
        assert payment.status == "PENDING"

        # 9. SIMULATE PAYMENT GATEWAY REDIRECT (USER PAYS)
        # In real flow, user would be redirected to Zarinpal, pay, and return

        # 10. VERIFY PAYMENT (CALLBACK FROM GATEWAY)
        # Mock Zarinpal verification
        responses.add(
            responses.POST,
            "https://payment.zarinpal.com/pg/v4/payment/verify.json",
            json={
                "data": {
                    "ref_id": "12345678",
                    "status": "success",
                    "card_pan": "123456******1234"
                },
                "errors": []
            },
            status=200
        )

        payment_verify_url = reverse("payment-verify")
        response = api_client.post(payment_verify_url, {
            "payment_id": payment.id,
            "authority": "A00000000000000000000000000123456",
            "status": "OK"
        })
        assert response.status_code == status.HTTP_200_OK

        # 11. VERIFY ORDER STATUS UPDATED
        order.refresh_from_db()
        assert order.status in ["PROCESSING", "CONFIRMED"]

        # 12. VERIFY INVOICE GENERATED
        assert Invoice.objects.filter(order=order).exists()
        invoice = Invoice.objects.get(order=order)
        assert invoice.total_amount == order.total_amount

        # 13. VERIFY STOCK REDUCED
        product1.refresh_from_db()
        product2.refresh_from_db()
        assert product1.stock == 8  # 10 - 2
        assert product2.stock == 4  # 5 - 1

        # 14. VERIFY CART IS EMPTY/INACTIVE
        cart_response = api_client.get(cart_url)
        assert len(cart_response.data["items"]) == 0


@pytest.mark.e2e
class TestAnonymousToAuthenticatedFlow:
    """Test flow for anonymous user who logs in."""

    def test_anonymous_cart_merge_on_login(self, api_client):
        """
        Test: Browse as guest → Add to cart → Login → Cart merged
        """
        # 1. BROWSE AS ANONYMOUS USER
        import uuid
        anonymous_id = str(uuid.uuid4())
        api_client.credentials(HTTP_X_ANONYMOUS_CART_ID=anonymous_id)

        # Create products
        product1 = ProductFactory(price=Decimal("100.00"), stock=10)
        product2 = ProductFactory(price=Decimal("50.00"), stock=10)

        # 2. ADD PRODUCTS TO ANONYMOUS CART
        add_to_cart_url = reverse("cart-add-item")
        response = api_client.post(add_to_cart_url, {
            "product_id": product1.id,
            "quantity": 1
        })
        assert response.status_code == status.HTTP_200_OK

        response = api_client.post(add_to_cart_url, {
            "product_id": product2.id,
            "quantity": 2
        })
        assert response.status_code == status.HTTP_200_OK

        # Verify anonymous cart has items
        cart_url = reverse("cart-details")
        response = api_client.get(cart_url)
        assert len(response.data["items"]) == 2

        # 3. CREATE ACCOUNT / LOGIN
        user = UserFactory(email="test@example.com", password="testpass123")
        login_url = reverse("user-login")
        response = api_client.post(login_url, {
            "email": "test@example.com",
            "password": "testpass123"
        })
        assert response.status_code == status.HTTP_200_OK
        access_token = response.data["access"]

        # Authenticate
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # 4. MERGE CART
        merge_url = reverse("cart-merge")
        response = api_client.post(merge_url, {"anonymous_id": anonymous_id})
        assert response.status_code == status.HTTP_200_OK

        # 5. VERIFY CART MERGED
        response = api_client.get(cart_url)
        assert len(response.data["items"]) == 2

        # Can now proceed with checkout as authenticated user


@pytest.mark.e2e
class TestOrderCancellationFlow:
    """Test order cancellation and refund flow."""

    def test_cancel_order_before_payment(self, authenticated_client, user):
        """Test cancelling order before payment."""
        # Create order
        from shop.tests.factories import create_order_with_items
        order = create_order_with_items(user=user, item_count=2, status="PENDING")

        # Cancel order
        cancel_url = reverse("order-cancel", kwargs={"id": order.id})
        response = authenticated_client.post(cancel_url)

        assert response.status_code == status.HTTP_200_OK

        order.refresh_from_db()
        assert order.status == "CANCELLED"

    def test_cannot_cancel_shipped_order(self, authenticated_client, user):
        """Test that shipped orders cannot be cancelled."""
        from shop.tests.factories import create_order_with_items
        order = create_order_with_items(user=user, item_count=1, status="SHIPPED")

        cancel_url = reverse("order-cancel", kwargs={"id": order.id})
        response = authenticated_client.post(cancel_url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.e2e
@pytest.mark.slow
class TestMultipleUsersSimultaneousCheckout:
    """Test concurrent checkout scenarios."""

    def test_multiple_users_buying_last_item(self, api_client):
        """
        Test race condition: Multiple users try to buy the last item.
        Only one should succeed.
        """
        # Create product with stock of 1
        product = ProductFactory(stock=1, price=Decimal("100.00"))

        # Create two users
        user1 = UserFactory(email="user1@example.com", password="pass123")
        user2 = UserFactory(email="user2@example.com", password="pass123")

        # Both users add to cart (this should succeed)
        from shop.tests.factories import CartFactory, CartItemFactory
        cart1 = CartFactory(user=user1)
        cart2 = CartFactory(user=user2)
        CartItemFactory(cart=cart1, product=product, quantity=1)
        CartItemFactory(cart=cart2, product=product, quantity=1)

        # Both try to checkout
        # First checkout should succeed
        checkout_url = reverse("cart-checkout")

        # User 1 checkouts first
        from rest_framework_simplejwt.tokens import RefreshToken
        token1 = RefreshToken.for_user(user1)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token1.access_token}")

        address1 = AddressFactory(user=user1)
        response1 = api_client.post(checkout_url, {
            "address_id": address1.id,
            "payment_method": "ONLINE"
        })

        # User 2 tries to checkout (should fail - out of stock)
        token2 = RefreshToken.for_user(user2)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token2.access_token}")

        address2 = AddressFactory(user=user2)
        response2 = api_client.post(checkout_url, {
            "address_id": address2.id,
            "payment_method": "ONLINE"
        })

        # Verify one succeeded and one failed
        assert (
            (response1.status_code == status.HTTP_201_CREATED and
             response2.status_code == status.HTTP_400_BAD_REQUEST) or
            (response1.status_code == status.HTTP_400_BAD_REQUEST and
             response2.status_code == status.HTTP_201_CREATED)
        )

        # Verify stock is 0
        product.refresh_from_db()
        assert product.stock == 0
