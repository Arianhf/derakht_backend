# users/tests/test_views/test_auth.py

from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status

from core.tests.base import BaseAPITestCase

User = get_user_model()


class AuthenticationEndpointTest(BaseAPITestCase):
    """Test cases for authentication endpoints"""

    def test_user_signup_success(self):
        """Test successful user registration"""
        url = "/api/users/signup/"
        data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "testpass123",
            "first_name": "New",
            "last_name": "User",
            "age": 25,
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)

        # Verify user was created
        user = User.objects.get(email="newuser@example.com")
        self.assertEqual(user.username, "newuser")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "User")

    def test_user_signup_duplicate_email(self):
        """Test signup with duplicate email fails"""
        # Create existing user
        self.create_user(email="existing@example.com", username="existing")

        url = "/api/users/signup/"
        data = {
            "email": "existing@example.com",
            "username": "newuser",
            "password": "testpass123",
            "first_name": "New",
            "last_name": "User",
            "age": 25,
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_signup_missing_required_fields(self):
        """Test signup with missing required fields fails"""
        url = "/api/users/signup/"
        data = {
            "email": "newuser@example.com",
            # Missing required fields
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_obtain_success(self):
        """Test obtaining JWT token with valid credentials"""
        # Create user
        user = self.create_user(
            email="test@example.com", username="testuser", password="testpass123"
        )

        url = "/api/users/login/"
        data = {"email": "test@example.com", "password": "testpass123"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_token_obtain_invalid_credentials(self):
        """Test obtaining token with invalid credentials fails"""
        # Create user
        self.create_user(
            email="test@example.com", username="testuser", password="testpass123"
        )

        url = "/api/users/login/"
        data = {"email": "test@example.com", "password": "wrongpassword"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_obtain_nonexistent_user(self):
        """Test obtaining token for nonexistent user fails"""
        url = "/api/users/login/"
        data = {"email": "nonexistent@example.com", "password": "testpass123"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_success(self):
        """Test refreshing JWT token"""
        # Create user and get tokens
        user = self.create_user(
            email="test@example.com", username="testuser", password="testpass123"
        )

        # Get initial tokens
        url = "/api/users/login/"
        data = {"email": "test@example.com", "password": "testpass123"}
        response = self.client.post(url, data, format="json")
        refresh_token = response.data["refresh"]

        # Refresh the token
        refresh_url = "/api/users/token/refresh/"
        refresh_data = {"refresh": refresh_token}
        refresh_response = self.client.post(refresh_url, refresh_data, format="json")

        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)

    def test_token_refresh_invalid_token(self):
        """Test refreshing with invalid token fails"""
        refresh_url = "/api/users/token/refresh/"
        refresh_data = {"refresh": "invalid_token"}
        response = self.client.post(refresh_url, refresh_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_user_profile_authenticated(self):
        """Test getting user profile when authenticated"""
        user = self.authenticate()

        url = "/api/users/me/"
        response = self.client.get(url)

        self.assertSuccess(response)
        self.assertEqual(response.data["email"], user.email)
        self.assertEqual(response.data["username"], user.username)

    def test_get_user_profile_unauthenticated(self):
        """Test getting user profile when not authenticated fails"""
        url = "/api/users/me/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_user_profile(self):
        """Test updating user profile"""
        user = self.authenticate()

        url = "/api/users/me/"
        data = {"first_name": "Updated", "last_name": "Name"}
        response = self.client.patch(url, data, format="json")

        self.assertSuccess(response)
        self.assertEqual(response.data["first_name"], "Updated")
        self.assertEqual(response.data["last_name"], "Name")

        # Verify in database
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Updated")
        self.assertEqual(user.last_name, "Name")

    def test_email_verification_success(self):
        """Test email verification with valid token"""
        # Create user with verification token
        user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            first_name="Test",
            last_name="User",
            age=25,
            email_verification_token="valid_token_123",
            is_verified=False,
        )

        url = "/api/users/verify-email/"
        data = {"email": "test@example.com", "token": "valid_token_123"}
        response = self.client.post(url, data, format="json")

        self.assertSuccess(response)
        self.assertIn("message", response.data)

        # Verify user is now verified
        user.refresh_from_db()
        self.assertTrue(user.is_verified)
        self.assertIsNone(user.email_verification_token)

    def test_email_verification_invalid_token(self):
        """Test email verification with invalid token fails"""
        # Create user
        user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
            first_name="Test",
            last_name="User",
            age=25,
            email_verification_token="valid_token_123",
            is_verified=False,
        )

        url = "/api/users/verify-email/"
        data = {"email": "test@example.com", "token": "invalid_token"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify user is still not verified
        user.refresh_from_db()
        self.assertFalse(user.is_verified)

    def test_user_login_creates_tokens(self):
        """Test user login endpoint (if exists)"""
        # This test depends on your URL configuration
        # Skip if the endpoint doesn't exist in the current setup
        pass


class AddressEndpointTest(BaseAPITestCase):
    """Test cases for address management endpoints"""

    def test_create_address_authenticated(self):
        """Test creating address when authenticated"""
        user = self.authenticate()

        url = "/api/users/addresses/"
        data = {
            "recipient_name": "Test Recipient",
            "address": "Test Street, Building 1",
            "city": "تهران",
            "province": "تهران",
            "postal_code": "1234567890",
            "phone_number": "+989123456789",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["recipient_name"], "Test Recipient")

    def test_create_address_unauthenticated(self):
        """Test creating address when not authenticated fails"""
        url = "/api/users/addresses/"
        data = {
            "recipient_name": "Test Recipient",
            "address": "Test Street",
            "city": "تهران",
            "province": "تهران",
            "postal_code": "1234567890",
            "phone_number": "+989123456789",
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_user_addresses(self):
        """Test listing user addresses"""
        from users.tests.fixtures import UserFixtures

        user = self.authenticate()

        # Create some addresses
        UserFixtures.create_address(user, recipient_name="Address 1")
        UserFixtures.create_address(user, recipient_name="Address 2")

        url = "/api/users/addresses/"
        response = self.client.get(url)

        self.assertSuccess(response)
        self.assertEqual(len(response.data), 2)

    def test_set_default_address(self):
        """Test setting an address as default"""
        from users.tests.fixtures import UserFixtures

        user = self.authenticate()

        # Create addresses
        address1 = UserFixtures.create_address(user, recipient_name="Address 1")
        address2 = UserFixtures.create_address(user, recipient_name="Address 2")

        url = f"/api/users/addresses/{address2.id}/set_default/"
        response = self.client.post(url, {}, format="json")

        self.assertSuccess(response)
        self.assertTrue(response.data["is_default"])

        # Verify address1 is no longer default
        address1.refresh_from_db()
        self.assertFalse(address1.is_default)
