import pytest
from django.contrib.auth import get_user_model
from shop.models import Product, Category
from decimal import Decimal

User = get_user_model()


@pytest.fixture
def user():
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123',
    )


@pytest.fixture
def category():
    return Category.objects.create(
        name='Test Category',
        slug='test-category',
    )


@pytest.fixture
def product(category):
    return Product.objects.create(
        title='Test Product',
        slug='test-product',
        price=Decimal('100.00'),
        category=category,
        is_available=True,
        is_visible=True,
    )
