# users/tests/test_models/test_user.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

User = get_user_model()


class UserPhoneValidationTest(TestCase):
    """Test cases for User phone number validation"""

    def test_create_user_without_phone_number(self):
        """Test creating user without phone number"""
        user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            first_name="Test",
            last_name="User",
            age=25,
        )
        self.assertIsNone(user.phone_number)

    def test_valid_iranian_phone_number(self):
        """Test user with valid Iranian phone number"""
        user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            first_name="Test",
            last_name="User",
            age=25,
            phone_number="+989123456789",
        )
        self.assertEqual(str(user.phone_number), "+989123456789")

    def test_iranian_phone_number_without_country_code(self):
        """Test Iranian phone number without country code is accepted"""
        user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            first_name="Test",
            last_name="User",
            age=25,
            phone_number="09123456789",
        )
        # The phone field should normalize it
        self.assertIsNotNone(user.phone_number)

    def test_iranian_phone_number_must_start_with_9(self):
        """Test that Iranian phone numbers must start with 9"""
        user = User(
            email="test@example.com",
            username="testuser",
            first_name="Test",
            last_name="User",
            age=25,
            phone_number="+988123456789",  # Starts with 8, not 9
        )

        with self.assertRaises(ValidationError) as context:
            user.save()

        self.assertIn("phone_number", str(context.exception))

    def test_iranian_phone_number_must_be_10_digits(self):
        """Test that Iranian phone numbers must be exactly 10 digits"""
        # Too short (9 digits)
        user = User(
            email="test1@example.com",
            username="testuser1",
            first_name="Test",
            last_name="User",
            age=25,
            phone_number="+98912345678",  # 9 digits
        )

        with self.assertRaises(ValidationError) as context:
            user.save()

        self.assertIn("phone_number", str(context.exception))

    def test_iranian_phone_number_various_valid_formats(self):
        """Test various valid Iranian phone number formats"""
        valid_numbers = [
            "+989123456789",
            "+989203456789",
            "+989303456789",
            "+989903456789",
        ]

        for idx, number in enumerate(valid_numbers):
            user = User.objects.create_user(
                email=f"test{idx}@example.com",
                username=f"testuser{idx}",
                password="testpass123",
                first_name="Test",
                last_name="User",
                age=25,
                phone_number=number,
            )
            self.assertIsNotNone(user.phone_number)

    def test_non_iranian_phone_number_rejected(self):
        """Test that non-Iranian phone numbers are rejected"""
        user = User(
            email="test@example.com",
            username="testuser",
            first_name="Test",
            last_name="User",
            age=25,
            phone_number="+14155552671",  # US number
        )

        with self.assertRaises(ValidationError) as context:
            user.save()

        self.assertIn("phone_number", str(context.exception))

    def test_invalid_phone_number_format(self):
        """Test that invalid phone number format is rejected"""
        user = User(
            email="test@example.com",
            username="testuser",
            first_name="Test",
            last_name="User",
            age=25,
            phone_number="invalid",
        )

        with self.assertRaises(ValidationError) as context:
            user.save()

        self.assertIn("phone_number", str(context.exception))

    def test_update_user_with_valid_phone(self):
        """Test updating user with valid phone number"""
        user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            first_name="Test",
            last_name="User",
            age=25,
        )

        # Update with valid phone
        user.phone_number = "+989123456789"
        user.save()

        self.assertEqual(str(user.phone_number), "+989123456789")

    def test_update_user_with_invalid_phone(self):
        """Test updating user with invalid phone number"""
        user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            first_name="Test",
            last_name="User",
            age=25,
        )

        # Try to update with invalid phone
        user.phone_number = "+988123456789"  # Doesn't start with 9

        with self.assertRaises(ValidationError):
            user.save()
