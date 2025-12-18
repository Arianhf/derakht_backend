# users/tests/fixtures.py

from django.contrib.auth import get_user_model
from users.models import Address

User = get_user_model()


class UserFixtures:
    """Test fixtures for user-related models"""

    @staticmethod
    def create_user(**kwargs):
        """
        Create a test user

        Returns:
            User instance
        """
        defaults = {
            "email": "testuser@example.com",
            "username": "testuser",
            "password": "testpass123",
            "first_name": "Test",
            "last_name": "User",
            "age": 25,
        }
        defaults.update(kwargs)

        # Extract password to use create_user method
        password = defaults.pop("password")
        user = User.objects.create_user(password=password, **defaults)
        return user

    @staticmethod
    def create_address(user, **kwargs):
        """
        Create a test address

        Args:
            user: User instance

        Returns:
            Address instance
        """
        defaults = {
            "user": user,
            "recipient_name": "Test Recipient",
            "address": "Test Street, Test Building, Unit 10",
            "city": "تهران",
            "province": "تهران",
            "postal_code": "1234567890",
            "phone_number": "+989123456789",
            "is_default": False,
        }
        defaults.update(kwargs)
        return Address.objects.create(**defaults)
