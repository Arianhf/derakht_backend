# core/tests/base.py

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from typing import Dict, Any, Optional

User = get_user_model()


class BaseTestCase(TestCase):
    """Base test class with common utilities for all tests"""

    @classmethod
    def setUpTestData(cls):
        """Set up data for the whole test class (called once)"""
        super().setUpTestData()

    def setUp(self):
        """Set up before each test method"""
        super().setUp()

    def tearDown(self):
        """Clean up after each test method"""
        super().tearDown()

    def create_user(
        self,
        email: str = "testuser@example.com",
        username: str = "testuser",
        password: str = "testpass123",
        **kwargs
    ) -> User:
        """
        Helper method to create a test user

        Args:
            email: User email
            username: Username
            password: User password
            **kwargs: Additional user fields

        Returns:
            Created user instance
        """
        defaults = {
            "first_name": "Test",
            "last_name": "User",
            "age": 25,
        }
        defaults.update(kwargs)

        user = User.objects.create_user(
            email=email, username=username, password=password, **defaults
        )
        return user

    def create_superuser(
        self,
        email: str = "admin@example.com",
        username: str = "admin",
        password: str = "adminpass123",
        **kwargs
    ) -> User:
        """Helper method to create a test superuser"""
        defaults = {
            "first_name": "Admin",
            "last_name": "User",
            "age": 30,
        }
        defaults.update(kwargs)

        user = User.objects.create_superuser(
            email=email, username=username, password=password, **defaults
        )
        return user


class BaseTransactionTestCase(TransactionTestCase):
    """Base transaction test class for tests requiring database transactions"""

    def setUp(self):
        """Set up before each test method"""
        super().setUp()

    def tearDown(self):
        """Clean up after each test method"""
        super().tearDown()

    def create_user(
        self,
        email: str = "testuser@example.com",
        username: str = "testuser",
        password: str = "testpass123",
        **kwargs
    ) -> User:
        """Helper method to create a test user"""
        defaults = {
            "first_name": "Test",
            "last_name": "User",
            "age": 25,
        }
        defaults.update(kwargs)

        user = User.objects.create_user(
            email=email, username=username, password=password, **defaults
        )
        return user


class BaseAPITestCase(APITestCase):
    """Base API test class with common utilities for API tests"""

    def setUp(self):
        """Set up before each test method"""
        super().setUp()
        self.client = APIClient()

    def tearDown(self):
        """Clean up after each test method"""
        super().tearDown()

    def create_user(
        self,
        email: str = "testuser@example.com",
        username: str = "testuser",
        password: str = "testpass123",
        **kwargs
    ) -> User:
        """Helper method to create a test user"""
        defaults = {
            "first_name": "Test",
            "last_name": "User",
            "age": 25,
        }
        defaults.update(kwargs)

        user = User.objects.create_user(
            email=email, username=username, password=password, **defaults
        )
        return user

    def authenticate(self, user: Optional[User] = None) -> User:
        """
        Authenticate a user for API tests

        Args:
            user: User to authenticate. If None, creates a new user.

        Returns:
            Authenticated user instance
        """
        if user is None:
            user = self.create_user()

        self.client.force_authenticate(user=user)
        return user

    def logout(self):
        """Log out the current user"""
        self.client.force_authenticate(user=None)

    def assertValidationError(
        self, response, field: str = None, status_code: int = 400
    ):
        """
        Assert that response contains a validation error

        Args:
            response: API response
            field: Optional field name to check for error
            status_code: Expected status code (default: 400)
        """
        self.assertEqual(response.status_code, status_code)
        if field:
            self.assertIn(field, response.data)

    def assertSuccess(self, response, status_code: int = 200):
        """
        Assert that response is successful

        Args:
            response: API response
            status_code: Expected status code (default: 200)
        """
        self.assertEqual(response.status_code, status_code)
