# users/tests/test_models/test_address.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from users.models import Address

User = get_user_model()


class AddressDefaultAssignmentTest(TestCase):
    """Test cases for Address default assignment logic"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            first_name="Test",
            last_name="User",
            age=25,
        )

    def test_first_address_is_default(self):
        """Test that the first address for a user is automatically set as default"""
        address = Address.objects.create(
            user=self.user,
            recipient_name="Test Recipient",
            address="Test Street",
            city="تهران",
            province="تهران",
            postal_code="1234567890",
            phone_number="+989123456789",
        )

        # First address should be default
        address.refresh_from_db()
        self.assertTrue(address.is_default)

    def test_first_address_is_default_even_if_set_to_false(self):
        """Test that first address becomes default even if explicitly set to False"""
        address = Address.objects.create(
            user=self.user,
            recipient_name="Test Recipient",
            address="Test Street",
            city="تهران",
            province="تهران",
            postal_code="1234567890",
            phone_number="+989123456789",
            is_default=False,
        )

        # Should still be default as it's the first address
        address.refresh_from_db()
        self.assertTrue(address.is_default)

    def test_second_address_is_not_default(self):
        """Test that second address is not default by default"""
        # Create first address
        Address.objects.create(
            user=self.user,
            recipient_name="First Address",
            address="Test Street 1",
            city="تهران",
            province="تهران",
            postal_code="1234567890",
            phone_number="+989123456789",
        )

        # Create second address
        address2 = Address.objects.create(
            user=self.user,
            recipient_name="Second Address",
            address="Test Street 2",
            city="تهران",
            province="تهران",
            postal_code="1234567891",
            phone_number="+989123456788",
        )

        self.assertFalse(address2.is_default)

    def test_setting_new_address_as_default_unsets_previous(self):
        """Test that setting a new address as default unsets the previous default"""
        # Create first address (will be default)
        address1 = Address.objects.create(
            user=self.user,
            recipient_name="First Address",
            address="Test Street 1",
            city="تهران",
            province="تهران",
            postal_code="1234567890",
            phone_number="+989123456789",
        )

        # Create second address as default
        address2 = Address.objects.create(
            user=self.user,
            recipient_name="Second Address",
            address="Test Street 2",
            city="تهران",
            province="تهران",
            postal_code="1234567891",
            phone_number="+989123456788",
            is_default=True,
        )

        # Refresh first address from database
        address1.refresh_from_db()

        # First address should no longer be default
        self.assertFalse(address1.is_default)
        # Second address should be default
        self.assertTrue(address2.is_default)

    def test_updating_existing_address_to_default(self):
        """Test updating an existing address to be default"""
        # Create two addresses
        address1 = Address.objects.create(
            user=self.user,
            recipient_name="First Address",
            address="Test Street 1",
            city="تهران",
            province="تهران",
            postal_code="1234567890",
            phone_number="+989123456789",
        )

        address2 = Address.objects.create(
            user=self.user,
            recipient_name="Second Address",
            address="Test Street 2",
            city="تهران",
            province="تهران",
            postal_code="1234567891",
            phone_number="+989123456788",
        )

        # Update second address to be default
        address2.is_default = True
        address2.save()

        # Refresh first address
        address1.refresh_from_db()

        # Check states
        self.assertFalse(address1.is_default)
        self.assertTrue(address2.is_default)

    def test_multiple_addresses_only_one_default(self):
        """Test that only one address can be default at a time"""
        # Create three addresses
        address1 = Address.objects.create(
            user=self.user,
            recipient_name="First Address",
            address="Test Street 1",
            city="تهران",
            province="تهران",
            postal_code="1234567890",
            phone_number="+989123456789",
        )

        address2 = Address.objects.create(
            user=self.user,
            recipient_name="Second Address",
            address="Test Street 2",
            city="تهران",
            province="تهران",
            postal_code="1234567891",
            phone_number="+989123456788",
        )

        address3 = Address.objects.create(
            user=self.user,
            recipient_name="Third Address",
            address="Test Street 3",
            city="اصفهان",
            province="اصفهان",
            postal_code="1234567892",
            phone_number="+989123456787",
            is_default=True,
        )

        # Refresh all addresses
        address1.refresh_from_db()
        address2.refresh_from_db()

        # Only third address should be default
        self.assertFalse(address1.is_default)
        self.assertFalse(address2.is_default)
        self.assertTrue(address3.is_default)

        # Verify only one default exists in database
        default_count = Address.objects.filter(user=self.user, is_default=True).count()
        self.assertEqual(default_count, 1)

    def test_different_users_can_have_default_addresses(self):
        """Test that different users can each have their own default address"""
        user2 = User.objects.create_user(
            email="test2@example.com",
            username="testuser2",
            password="testpass123",
            first_name="Test2",
            last_name="User2",
            age=30,
        )

        # Create default address for first user
        address1 = Address.objects.create(
            user=self.user,
            recipient_name="User 1 Address",
            address="Test Street 1",
            city="تهران",
            province="تهران",
            postal_code="1234567890",
            phone_number="+989123456789",
        )

        # Create default address for second user
        address2 = Address.objects.create(
            user=user2,
            recipient_name="User 2 Address",
            address="Test Street 2",
            city="اصفهان",
            province="اصفهان",
            postal_code="1234567891",
            phone_number="+989123456788",
        )

        # Both should be default
        self.assertTrue(address1.is_default)
        self.assertTrue(address2.is_default)

    def test_address_ordering(self):
        """Test that addresses are ordered by default status and created_at"""
        # Create multiple addresses
        address1 = Address.objects.create(
            user=self.user,
            recipient_name="First Address",
            address="Test Street 1",
            city="تهران",
            province="تهران",
            postal_code="1234567890",
            phone_number="+989123456789",
        )

        address2 = Address.objects.create(
            user=self.user,
            recipient_name="Second Address",
            address="Test Street 2",
            city="تهران",
            province="تهران",
            postal_code="1234567891",
            phone_number="+989123456788",
        )

        address3 = Address.objects.create(
            user=self.user,
            recipient_name="Third Address",
            address="Test Street 3",
            city="تهران",
            province="تهران",
            postal_code="1234567892",
            phone_number="+989123456787",
            is_default=True,
        )

        # Get addresses in order
        addresses = list(Address.objects.filter(user=self.user))

        # Default address should be first
        self.assertEqual(addresses[0].id, address3.id)
        self.assertTrue(addresses[0].is_default)
