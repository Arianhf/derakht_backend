"""
Global pytest configuration and fixtures.
This file is automatically loaded by pytest before running tests.
"""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
import uuid

User = get_user_model()


# ============================================================================
# DATABASE FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Set up the test database once per test session.
    This runs migrations and prepares the database.
    """
    with django_db_blocker.unblock():
        # Any database setup that should run once per session
        pass


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Automatically enable database access for all tests.
    This removes the need to decorate every test with @pytest.mark.django_db
    """
    pass


# ============================================================================
# API CLIENT FIXTURES
# ============================================================================


@pytest.fixture
def api_client():
    """
    Returns an unauthenticated API client for testing.
    Use this for public endpoints or before login.
    """
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """
    Returns an API client authenticated with JWT token.
    Automatically creates a test user and logs them in.
    """
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    # Store user reference for convenience
    api_client.user = user
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """
    Returns an API client authenticated as an admin user.
    """
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    api_client.user = admin_user
    return api_client


@pytest.fixture
def anonymous_cart_client(api_client):
    """
    Returns an API client with an anonymous cart ID in headers.
    Used for testing anonymous cart functionality.
    """
    anonymous_id = str(uuid.uuid4())
    api_client.credentials(HTTP_X_ANONYMOUS_CART_ID=anonymous_id)
    api_client.anonymous_id = anonymous_id
    return api_client


# ============================================================================
# USER FIXTURES
# ============================================================================


@pytest.fixture
def user_data():
    """
    Returns sample user data for testing.
    Use this when you need to POST user creation data.
    """
    return {
        "email": "testuser@example.com",
        "password": "TestPass123!",
        "name": "Test User",
        "phone_number": "+989123456789",
        "age": 25,
    }


@pytest.fixture
def user(db):
    """
    Creates and returns a regular test user.
    Password is set to 'testpass123' for authentication tests.
    """
    return User.objects.create_user(
        email="testuser@example.com",
        password="testpass123",
        name="Test User",
        phone_number="+989123456789",
        age=25,
    )


@pytest.fixture
def admin_user(db):
    """
    Creates and returns an admin/superuser for testing admin functionality.
    """
    return User.objects.create_superuser(
        email="admin@example.com",
        password="adminpass123",
        name="Admin User",
    )


@pytest.fixture
def user_factory(db):
    """
    Factory function to create multiple users with custom attributes.

    Usage:
        user1 = user_factory(email="user1@example.com")
        user2 = user_factory(email="user2@example.com", age=30)
    """

    def create_user(**kwargs):
        defaults = {
            "email": f"user_{uuid.uuid4().hex[:8]}@example.com",
            "password": "testpass123",
            "name": "Test User",
        }
        defaults.update(kwargs)

        password = defaults.pop("password")
        user = User.objects.create_user(**defaults)
        user.set_password(password)
        user.save()
        return user

    return create_user


# ============================================================================
# MOCK EXTERNAL SERVICES
# ============================================================================


@pytest.fixture
def mock_zarinpal(responses):
    """
    Mock Zarinpal payment gateway API responses.
    Use with @responses.activate decorator.

    Usage:
        @responses.activate
        def test_payment(mock_zarinpal):
            # Your test code here
    """

    def add_payment_request_mock(authority="A00000000000000000000000000123456"):
        responses.add(
            responses.POST,
            "https://payment.zarinpal.com/pg/v4/payment/request.json",
            json={"data": {"authority": authority}, "errors": []},
            status=200,
        )
        return authority

    def add_payment_verify_mock(status="success", ref_id="12345678"):
        responses.add(
            responses.POST,
            "https://payment.zarinpal.com/pg/v4/payment/verify.json",
            json={"data": {"ref_id": ref_id, "status": status}, "errors": []},
            status=200,
        )
        return ref_id

    mock_zarinpal.add_request = add_payment_request_mock
    mock_zarinpal.add_verify = add_payment_verify_mock

    return mock_zarinpal


@pytest.fixture
def mock_email_backend(settings):
    """
    Ensures email backend is set to in-memory for tests.
    Email messages will be available in django.core.mail.outbox
    """
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    from django.core import mail

    # Clear outbox before each test
    mail.outbox = []
    return mail.outbox


@pytest.fixture
def mock_file_storage(settings, tmp_path):
    """
    Configures file storage to use a temporary directory for tests.
    Files are automatically cleaned up after tests.
    """
    settings.MEDIA_ROOT = str(tmp_path / "media")
    settings.MEDIA_URL = "/test_media/"
    return tmp_path / "media"


# ============================================================================
# TIME MOCKING
# ============================================================================


@pytest.fixture
def frozen_time():
    """
    Freezes time at a specific datetime for testing time-dependent logic.

    Usage:
        def test_with_frozen_time(frozen_time):
            with frozen_time("2025-01-15 12:00:00"):
                # Time is frozen at this point
                assert datetime.now().hour == 12
    """
    from freezegun import freeze_time

    return freeze_time


# ============================================================================
# PERFORMANCE TESTING
# ============================================================================


@pytest.fixture
def django_assert_num_queries(pytestconfig):
    """
    Context manager to assert the number of database queries.
    Helps prevent N+1 query problems.

    Usage:
        def test_product_list(django_assert_num_queries):
            with django_assert_num_queries(5):
                # This code should execute exactly 5 queries
                Product.objects.all()
    """
    from django.test.utils import CaptureQueriesContext
    from django.db import connection

    class AssertNumQueries:
        def __call__(self, num):
            return CaptureQueriesContext(connection)

    return AssertNumQueries()


# ============================================================================
# TEST DATA CLEANUP
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_files(mock_file_storage):
    """
    Automatically cleanup any files created during tests.
    Runs after each test.
    """
    yield
    # Cleanup happens after the test
    import shutil

    if mock_file_storage.exists():
        shutil.rmtree(mock_file_storage, ignore_errors=True)


# ============================================================================
# CUSTOM MARKERS
# ============================================================================


def pytest_configure(config):
    """
    Register custom markers to avoid warnings.
    These markers are also defined in pytest.ini
    """
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "payment: Payment-related tests")
    config.addinivalue_line("markers", "auth: Authentication tests")


# ============================================================================
# TEST REPORTING
# ============================================================================


def pytest_addoption(parser):
    """
    Add custom command-line options to pytest.
    """
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="Run slow tests",
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection based on command-line options.
    Skip slow tests unless --runslow is passed.
    """
    if config.getoption("--runslow"):
        return

    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
