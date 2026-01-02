from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from shop.models import Cart, Product, Category, PromoCode, CartItem
from shop.services.cart import CartService
from datetime import timedelta
from django.utils import timezone
import uuid

User = get_user_model()


class CartServiceTestCase(TestCase):
    """Tests for CartService"""

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
            is_available=True,
            is_visible=True,
            stock=10,
        )

    def test_get_or_create_cart_for_user(self):
        """Test creating cart for authenticated user"""
        cart, created = CartService.get_or_create_cart(user=self.user)

        self.assertTrue(created)
        self.assertEqual(cart.user, self.user)
        self.assertIsNone(cart.anonymous_id)

        # Getting again should return same cart
        cart2, created2 = CartService.get_or_create_cart(user=self.user)
        self.assertFalse(created2)
        self.assertEqual(cart.id, cart2.id)

    def test_get_or_create_cart_anonymous(self):
        """Test creating cart for anonymous user"""
        anon_id = uuid.uuid4()

        cart, created = CartService.get_or_create_cart(anonymous_id=anon_id)

        self.assertTrue(created)
        self.assertEqual(cart.anonymous_id, anon_id)
        self.assertIsNone(cart.user)

    def test_get_or_create_cart_requires_user_or_anonymous(self):
        """Test that either user or anonymous_id is required"""
        with self.assertRaises(ValueError) as cm:
            CartService.get_or_create_cart()

        self.assertIn("Either user or anonymous_id required", str(cm.exception))

    def test_add_item_to_cart(self):
        """Test adding item to cart"""
        cart, _ = CartService.get_or_create_cart(user=self.user)

        cart_item = CartService.add_item(cart, self.product, 2)

        self.assertEqual(cart_item.cart, cart)
        self.assertEqual(cart_item.product, self.product)
        self.assertEqual(cart_item.quantity, 2)

    def test_add_item_increases_quantity(self):
        """Test adding same item increases quantity"""
        cart, _ = CartService.get_or_create_cart(user=self.user)

        CartService.add_item(cart, self.product, 2)
        cart_item = CartService.add_item(cart, self.product, 3)

        self.assertEqual(cart_item.quantity, 5)

    def test_add_unavailable_product_fails(self):
        """Test adding unavailable product raises error"""
        cart, _ = CartService.get_or_create_cart(user=self.user)
        self.product.is_available = False
        self.product.save()

        with self.assertRaises(ValueError) as cm:
            CartService.add_item(cart, self.product, 1)

        self.assertIn("not available", str(cm.exception))

    def test_add_item_exceeding_stock_fails(self):
        """Test adding more items than stock raises error"""
        cart, _ = CartService.get_or_create_cart(user=self.user)

        with self.assertRaises(ValueError) as cm:
            CartService.add_item(cart, self.product, 20)  # stock is 10

        self.assertIn("items available", str(cm.exception))

    def test_add_invalid_quantity_fails(self):
        """Test adding zero or negative quantity fails"""
        cart, _ = CartService.get_or_create_cart(user=self.user)

        with self.assertRaises(ValueError) as cm:
            CartService.add_item(cart, self.product, 0)

        self.assertIn("must be positive", str(cm.exception))

    def test_update_quantity(self):
        """Test updating item quantity"""
        cart, _ = CartService.get_or_create_cart(user=self.user)
        CartService.add_item(cart, self.product, 2)

        cart_item = CartService.update_quantity(cart, self.product, 5)

        self.assertEqual(cart_item.quantity, 5)

    def test_update_quantity_to_zero_removes_item(self):
        """Test updating quantity to 0 removes item"""
        cart, _ = CartService.get_or_create_cart(user=self.user)
        CartService.add_item(cart, self.product, 2)

        result = CartService.update_quantity(cart, self.product, 0)

        self.assertIsNone(result)
        self.assertEqual(cart.items.count(), 0)

    def test_update_quantity_negative_fails(self):
        """Test updating to negative quantity fails"""
        cart, _ = CartService.get_or_create_cart(user=self.user)
        CartService.add_item(cart, self.product, 2)

        with self.assertRaises(ValueError) as cm:
            CartService.update_quantity(cart, self.product, -1)

        self.assertIn("cannot be negative", str(cm.exception))

    def test_apply_valid_promo_code(self):
        """Test applying valid promo code"""
        cart, _ = CartService.get_or_create_cart(user=self.user)
        CartService.add_item(cart, self.product, 2)  # Total: 200

        promo = PromoCode.objects.create(
            code='SUMMER10',
            discount_type='percentage',
            discount_value=10,
            min_purchase=100,
            valid_from=timezone.now() - timedelta(days=1),
            valid_to=timezone.now() + timedelta(days=7),
            is_active=True,
        )

        promo_returned, discount = CartService.apply_promo_code(cart, 'SUMMER10')

        self.assertEqual(promo_returned, promo)
        self.assertEqual(discount, Decimal('20.00'))  # 10% of 200

        cart.refresh_from_db()
        self.assertEqual(cart.promo_code, promo)
        self.assertEqual(cart.discount_amount, Decimal('20.00'))

    def test_apply_invalid_promo_code_fails(self):
        """Test applying invalid promo code raises error"""
        cart, _ = CartService.get_or_create_cart(user=self.user)

        with self.assertRaises(ValueError) as cm:
            CartService.apply_promo_code(cart, 'INVALID')

        self.assertIn("Invalid or expired", str(cm.exception))

    def test_apply_promo_below_minimum_fails(self):
        """Test applying promo code below minimum purchase fails"""
        cart, _ = CartService.get_or_create_cart(user=self.user)
        CartService.add_item(cart, self.product, 1)  # Total: 100

        promo = PromoCode.objects.create(
            code='BIG50',
            discount_type='percentage',
            discount_value=50,
            min_purchase=500,
            valid_from=timezone.now() - timedelta(days=1),
            valid_to=timezone.now() + timedelta(days=7),
            is_active=True,
        )

        with self.assertRaises(ValueError) as cm:
            CartService.apply_promo_code(cart, 'BIG50')

        self.assertIn("Minimum purchase", str(cm.exception))

    def test_apply_promo_max_uses_exceeded_fails(self):
        """Test applying promo code that reached max uses fails"""
        cart, _ = CartService.get_or_create_cart(user=self.user)
        CartService.add_item(cart, self.product, 2)  # Total: 200

        promo = PromoCode.objects.create(
            code='LIMITED',
            discount_type='percentage',
            discount_value=10,
            min_purchase=100,
            valid_from=timezone.now() - timedelta(days=1),
            valid_to=timezone.now() + timedelta(days=7),
            is_active=True,
            max_uses=5,
            used_count=5,
        )

        with self.assertRaises(ValueError) as cm:
            CartService.apply_promo_code(cart, 'LIMITED')

        self.assertIn("usage limit", str(cm.exception))

    def test_calculate_total(self):
        """Test cart total calculation"""
        cart, _ = CartService.get_or_create_cart(user=self.user)
        CartService.add_item(cart, self.product, 2)  # 200

        total = CartService.calculate_total(cart)
        self.assertEqual(total, Decimal('200.00'))

        # With discount
        cart.discount_amount = Decimal('20.00')
        cart.save()

        total = CartService.calculate_total(cart)
        self.assertEqual(total, Decimal('180.00'))

    def test_calculate_total_empty_cart(self):
        """Test calculating total for empty cart"""
        cart, _ = CartService.get_or_create_cart(user=self.user)

        total = CartService.calculate_total(cart)
        self.assertEqual(total, Decimal('0'))

    def test_clear_cart(self):
        """Test clearing cart"""
        cart, _ = CartService.get_or_create_cart(user=self.user)
        CartService.add_item(cart, self.product, 2)
        cart.discount_amount = Decimal('10.00')
        cart.save()

        CartService.clear_cart(cart)

        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 0)
        self.assertIsNone(cart.promo_code)
        self.assertEqual(cart.discount_amount, Decimal('0'))
