"""
Users app-specific pytest fixtures.
"""

import pytest
from users.tests.factories import UserFactory, AddressFactory, create_user_with_addresses


@pytest.fixture
def user_factory():
    """Returns the UserFactory for creating custom users."""
    return UserFactory


@pytest.fixture
def address_factory():
    """Returns the AddressFactory for creating custom addresses."""
    return AddressFactory


@pytest.fixture
def user_with_addresses():
    """Create a user with 2 addresses."""
    return create_user_with_addresses(address_count=2)


@pytest.fixture
def valid_signup_data():
    """Returns valid signup data for testing."""
    return {
        "email": "newuser@example.com",
        "password": "SecurePass123!",
        "name": "New User",
        "phone_number": "+989123456789",
        "age": 25,
    }


@pytest.fixture
def valid_login_data():
    """Returns valid login credentials."""
    return {"email": "testuser@example.com", "password": "testpass123"}
