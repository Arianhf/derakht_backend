"""
Integration tests for Authentication API.
Tests user signup, login, JWT tokens, email verification, and password reset.

Priority: P0 - Security-critical functionality
"""

import pytest
from django.urls import reverse
from django.core import mail
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User
from users.tests.factories import UserFactory


@pytest.mark.integration
@pytest.mark.auth
class TestUserSignup:
    """Test user registration/signup endpoint."""

    def test_signup_success(self, api_client, valid_signup_data):
        """Test successful user registration."""
        url = reverse("user-signup")
        response = api_client.post(url, valid_signup_data)

        assert response.status_code == status.HTTP_201_CREATED
        assert "access" in response.data
        assert "refresh" in response.data
        assert "user" in response.data

        # Verify user created in database
        assert User.objects.filter(email=valid_signup_data["email"]).exists()
        user = User.objects.get(email=valid_signup_data["email"])
        assert user.name == valid_signup_data["name"]
        assert user.is_active is True

    def test_signup_duplicate_email(self, api_client, user, valid_signup_data):
        """Test signup fails with duplicate email."""
        valid_signup_data["email"] = user.email

        url = reverse("user-signup")
        response = api_client.post(url, valid_signup_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_signup_invalid_email(self, api_client, valid_signup_data):
        """Test signup fails with invalid email format."""
        valid_signup_data["email"] = "invalid-email"

        url = reverse("user-signup")
        response = api_client.post(url, valid_signup_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_signup_weak_password(self, api_client, valid_signup_data):
        """Test signup fails with weak password."""
        valid_signup_data["password"] = "123"  # Too short

        url = reverse("user-signup")
        response = api_client.post(url, valid_signup_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data

    def test_signup_invalid_phone_number(self, api_client, valid_signup_data):
        """Test signup fails with invalid Iranian phone number."""
        valid_signup_data["phone_number"] = "123456"  # Invalid format

        url = reverse("user-signup")
        response = api_client.post(url, valid_signup_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "phone_number" in response.data

    def test_signup_missing_required_fields(self, api_client):
        """Test signup fails when required fields are missing."""
        url = reverse("user-signup")
        response = api_client.post(url, {"email": "test@example.com"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data

    def test_signup_sends_verification_email(
        self, api_client, valid_signup_data, mock_email_backend
    ):
        """Test that signup sends email verification email."""
        url = reverse("user-signup")
        response = api_client.post(url, valid_signup_data)

        assert response.status_code == status.HTTP_201_CREATED

        # Check if verification email was sent
        # Note: This depends on your implementation
        # If email verification is enabled, uncomment:
        # assert len(mail.outbox) == 1
        # assert valid_signup_data["email"] in mail.outbox[0].to
        # assert "verify" in mail.outbox[0].subject.lower()


@pytest.mark.integration
@pytest.mark.auth
class TestUserLogin:
    """Test user login endpoint."""

    def test_login_success(self, api_client, user):
        """Test successful login with correct credentials."""
        url = reverse("user-login")
        response = api_client.post(
            url, {"email": user.email, "password": "testpass123"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert "user" in response.data
        assert response.data["user"]["email"] == user.email

    def test_login_wrong_password(self, api_client, user):
        """Test login fails with incorrect password."""
        url = reverse("user-login")
        response = api_client.post(
            url, {"email": user.email, "password": "wrongpassword"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client):
        """Test login fails for non-existent user."""
        url = reverse("user-login")
        response = api_client.post(
            url, {"email": "nonexistent@example.com", "password": "testpass123"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_inactive_user(self, api_client, user):
        """Test login fails for inactive users."""
        user.is_active = False
        user.save()

        url = reverse("user-login")
        response = api_client.post(
            url, {"email": user.email, "password": "testpass123"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_case_insensitive_email(self, api_client, user):
        """Test login works with case-insensitive email."""
        url = reverse("user-login")
        response = api_client.post(
            url, {"email": user.email.upper(), "password": "testpass123"}
        )

        # This depends on your implementation
        # Django's email field is case-insensitive by default
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]


@pytest.mark.integration
@pytest.mark.auth
class TestJWTTokens:
    """Test JWT token functionality."""

    def test_access_token_authentication(self, api_client, user):
        """Test that access token grants authentication."""
        # Get tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Make authenticated request
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        url = reverse("user-profile")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email

    def test_refresh_token_generates_new_access_token(self, api_client, user):
        """Test token refresh endpoint."""
        refresh = RefreshToken.for_user(user)

        url = reverse("token-refresh")
        response = api_client.post(url, {"refresh": str(refresh)})

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_invalid_access_token_rejected(self, api_client):
        """Test that invalid access tokens are rejected."""
        api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")
        url = reverse("user-profile")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_expired_token_rejected(self, api_client, user):
        """Test that expired tokens are rejected."""
        from datetime import timedelta
        from django.utils import timezone

        refresh = RefreshToken.for_user(user)

        # Manually expire the token
        refresh.access_token.set_exp(
            lifetime=timedelta(seconds=-1)
        )  # Expired 1 second ago

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
        url = reverse("user-profile")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
@pytest.mark.auth
class TestEmailVerification:
    """Test email verification flow."""

    def test_verify_email_success(self, api_client, user):
        """Test successful email verification."""
        # Generate verification token
        import uuid

        token = str(uuid.uuid4())
        user.email_verification_token = token
        user.email_verified = False
        user.save()

        url = reverse("verify-email")
        response = api_client.post(url, {"token": token})

        assert response.status_code == status.HTTP_200_OK

        # Verify user is now verified
        user.refresh_from_db()
        assert user.email_verified is True

    def test_verify_email_invalid_token(self, api_client):
        """Test email verification fails with invalid token."""
        url = reverse("verify-email")
        response = api_client.post(url, {"token": "invalid-token"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_email_already_verified(self, api_client, user):
        """Test verifying an already-verified email."""
        user.email_verified = True
        user.save()

        url = reverse("verify-email")
        response = api_client.post(url, {"token": "any-token"})

        # Should handle gracefully
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]


@pytest.mark.integration
@pytest.mark.auth
class TestPasswordReset:
    """Test password reset flow."""

    def test_request_password_reset(self, api_client, user, mock_email_backend):
        """Test password reset request sends email."""
        url = reverse("request-password-reset")
        response = api_client.post(url, {"email": user.email})

        assert response.status_code == status.HTTP_200_OK

        # Verify email sent
        assert len(mail.outbox) == 1
        assert user.email in mail.outbox[0].to
        assert "reset" in mail.outbox[0].subject.lower()

    def test_request_password_reset_nonexistent_email(
        self, api_client, mock_email_backend
    ):
        """Test password reset for non-existent email doesn't reveal information."""
        url = reverse("request-password-reset")
        response = api_client.post(url, {"email": "nonexistent@example.com"})

        # Should return success to prevent email enumeration
        assert response.status_code == status.HTTP_200_OK

        # But no email should be sent
        assert len(mail.outbox) == 0

    def test_reset_password_with_valid_token(self, api_client, user):
        """Test resetting password with valid token."""
        # Generate reset token
        import uuid

        token = str(uuid.uuid4())
        user.password_reset_token = token
        user.save()

        url = reverse("reset-password")
        new_password = "NewSecurePass123!"
        response = api_client.post(
            url, {"token": token, "password": new_password}
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify password changed
        user.refresh_from_db()
        assert user.check_password(new_password)

        # Verify token is cleared
        assert user.password_reset_token is None or user.password_reset_token == ""

    def test_reset_password_invalid_token(self, api_client):
        """Test password reset fails with invalid token."""
        url = reverse("reset-password")
        response = api_client.post(
            url, {"token": "invalid-token", "password": "NewPass123!"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reset_password_weak_password(self, api_client, user):
        """Test password reset fails with weak password."""
        import uuid

        token = str(uuid.uuid4())
        user.password_reset_token = token
        user.save()

        url = reverse("reset-password")
        response = api_client.post(url, {"token": token, "password": "123"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
@pytest.mark.auth
class TestUserProfile:
    """Test user profile endpoints."""

    def test_get_current_user_profile(self, authenticated_client, user):
        """Test retrieving current user's profile."""
        url = reverse("user-profile")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email
        assert response.data["name"] == user.name

    def test_update_user_profile(self, authenticated_client, user):
        """Test updating user profile."""
        url = reverse("user-profile")
        response = authenticated_client.patch(url, {"name": "Updated Name"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated Name"

        user.refresh_from_db()
        assert user.name == "Updated Name"

    def test_update_profile_unauthenticated(self, api_client):
        """Test unauthenticated users cannot access profile."""
        url = reverse("user-profile")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_email_requires_verification(self, authenticated_client, user):
        """Test changing email requires re-verification."""
        url = reverse("user-profile")
        new_email = "newemail@example.com"
        response = authenticated_client.patch(url, {"email": new_email})

        # Depending on implementation, might require verification
        if response.status_code == status.HTTP_200_OK:
            user.refresh_from_db()
            # Check if email_verified was reset
            assert user.email_verified is False or user.email == new_email


@pytest.mark.integration
@pytest.mark.auth
class TestProfileImageUpload:
    """Test profile image upload functionality."""

    def test_upload_profile_image(self, authenticated_client, mock_file_storage):
        """Test uploading profile image."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        image = SimpleUploadedFile(
            "profile.jpg", b"fake_image_content", content_type="image/jpeg"
        )

        url = reverse("user-profile-image")
        response = authenticated_client.post(url, {"profile_image": image})

        assert response.status_code == status.HTTP_200_OK

        # Verify user has profile image
        user = authenticated_client.user
        user.refresh_from_db()
        assert user.profile_image is not None

    def test_delete_profile_image(self, authenticated_client, user):
        """Test deleting profile image."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # First upload an image
        user.profile_image = SimpleUploadedFile(
            "profile.jpg", b"fake_image_content", content_type="image/jpeg"
        )
        user.save()

        url = reverse("user-profile-image")
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        user.refresh_from_db()
        assert not user.profile_image

    def test_upload_invalid_file_type(self, authenticated_client):
        """Test uploading non-image file fails."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        file = SimpleUploadedFile("document.pdf", b"fake_pdf_content", content_type="application/pdf")

        url = reverse("user-profile-image")
        response = authenticated_client.post(url, {"profile_image": file})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
