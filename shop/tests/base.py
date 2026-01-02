from django.test import TestCase
from django.contrib.auth import get_user_model
from shop.models import Product, Category, Cart
from decimal import Decimal

User = get_user_model()


class ShopTestCase(TestCase):
    """Base test case with common fixtures"""

    def setUp(self):
        """Set up test fixtures"""
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
        )

        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category',
        )

        # Create test products
        self.product1 = Product.objects.create(
            title='Test Product 1',
            slug='test-product-1',
            description='Test description',
            price=Decimal('100.00'),
            category=self.category,
            is_available=True,
            is_visible=True,
        )

        self.product2 = Product.objects.create(
            title='Test Product 2',
            slug='test-product-2',
            description='Test description 2',
            price=Decimal('200.00'),
            category=self.category,
            is_available=True,
            is_visible=True,
        )

    def create_cart(self, user=None, anonymous_id=None):
        """Helper to create test cart"""
        return Cart.objects.create(
            user=user,
            anonymous_id=anonymous_id,
            status='ACTIVE',
        )
