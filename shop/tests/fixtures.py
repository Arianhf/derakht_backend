# shop/tests/fixtures.py

from decimal import Decimal
from django.contrib.auth import get_user_model
from shop.models import Product, Cart, CartItem, Order, OrderItem, ShippingInfo, Payment
from shop.choices import OrderStatus, PaymentStatus, PaymentMethodProvider

User = get_user_model()


class ShopFixtures:
    """Test fixtures for shop-related models"""

    @staticmethod
    def create_product(**kwargs):
        """
        Create a test product

        Returns:
            Product instance
        """
        defaults = {
            "title": "Test Product",
            "description": "Test product description",
            "price": Decimal("100000"),
            "stock": 10,
            "sku": "TEST-SKU-001",
            "is_available": True,
            "slug": "test-product",
        }
        defaults.update(kwargs)
        return Product.objects.create(**defaults)

    @staticmethod
    def create_cart(user=None, anonymous_id=None, **kwargs):
        """
        Create a test cart

        Args:
            user: User instance (optional)
            anonymous_id: Anonymous cart ID (optional)

        Returns:
            Cart instance
        """
        defaults = {
            "user": user,
            "anonymous_id": anonymous_id,
        }
        defaults.update(kwargs)
        return Cart.objects.create(**defaults)

    @staticmethod
    def create_cart_item(cart, product, quantity=1, **kwargs):
        """
        Create a test cart item

        Args:
            cart: Cart instance
            product: Product instance
            quantity: Item quantity

        Returns:
            CartItem instance
        """
        defaults = {
            "cart": cart,
            "product": product,
            "quantity": quantity,
        }
        defaults.update(kwargs)
        return CartItem.objects.create(**defaults)

    @staticmethod
    def create_order(user, **kwargs):
        """
        Create a test order

        Args:
            user: User instance

        Returns:
            Order instance
        """
        defaults = {
            "user": user,
            "total_amount": 150000,
            "phone_number": "+989123456789",
            "status": OrderStatus.PENDING,
            "shipping_cost": 50000,
        }
        defaults.update(kwargs)
        return Order.objects.create(**defaults)

    @staticmethod
    def create_order_item(order, product, quantity=1, **kwargs):
        """
        Create a test order item

        Args:
            order: Order instance
            product: Product instance
            quantity: Item quantity

        Returns:
            OrderItem instance
        """
        price = kwargs.pop("price", product.price)
        defaults = {
            "order": order,
            "product": product,
            "quantity": quantity,
            "price": price,
        }
        defaults.update(kwargs)
        return OrderItem.objects.create(**defaults)

    @staticmethod
    def create_shipping_info(order, **kwargs):
        """
        Create test shipping information

        Args:
            order: Order instance

        Returns:
            ShippingInfo instance
        """
        defaults = {
            "order": order,
            "address": "Test Address, Unit 10",
            "city": "تهران",
            "province": "تهران",
            "postal_code": "1234567890",
            "recipient_name": "Test Recipient",
            "phone_number": "+989123456789",
        }
        defaults.update(kwargs)
        return ShippingInfo.objects.create(**defaults)

    @staticmethod
    def create_payment(order, **kwargs):
        """
        Create test payment

        Args:
            order: Order instance

        Returns:
            Payment instance
        """
        defaults = {
            "order": order,
            "amount": order.total_amount,
            "status": PaymentStatus.PENDING,
            "gateway": PaymentMethodProvider.ZARINPAL,
        }
        defaults.update(kwargs)
        return Payment.objects.create(**defaults)
