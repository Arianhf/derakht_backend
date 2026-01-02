# users/services/auth.py
from typing import Dict, Tuple
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
import jwt

from core.logging_utils import get_logger

logger = get_logger(__name__)
User = get_user_model()


class AuthService:
    """Business logic for authentication operations"""

    @staticmethod
    def generate_reset_token(user: User, expiry_hours: int = 24) -> str:
        """
        Generate password reset token using JWT

        Args:
            user: User requesting password reset
            expiry_hours: Token expiry time in hours (default 24)

        Returns:
            JWT token string

        Note:
            Token contains user_id and expiry timestamp
        """
        token = jwt.encode(
            {
                "user_id": str(user.id),
                "exp": datetime.utcnow() + timedelta(hours=expiry_hours),
                "type": "password_reset"
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )

        logger.info(
            "Password reset token generated",
            extra={"extra_data": {
                "user_id": str(user.id),
                "expiry_hours": expiry_hours,
            }}
        )

        return token

    @staticmethod
    def verify_reset_token(token: str) -> User:
        """
        Verify password reset token and return user

        Args:
            token: JWT token to verify

        Returns:
            User instance if token is valid

        Raises:
            ValueError: If token is invalid, expired, or user doesn't exist
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )

            if payload.get("type") != "password_reset":
                raise ValueError("Invalid token type")

            user = User.objects.get(id=payload["user_id"])

            logger.info(
                "Password reset token verified",
                extra={"extra_data": {"user_id": str(user.id)}}
            )

            return user

        except jwt.ExpiredSignatureError:
            logger.warning("Expired reset token used")
            raise ValueError("Reset link has expired")
        except jwt.InvalidTokenError:
            logger.warning("Invalid reset token used")
            raise ValueError("Invalid reset link")
        except User.DoesNotExist:
            logger.warning(f"Reset token for non-existent user")
            raise ValueError("Invalid reset link")

    @staticmethod
    def reset_password(user: User, new_password: str) -> User:
        """
        Reset user password

        Args:
            user: User to reset password for
            new_password: New password (plain text, will be hashed)

        Returns:
            Updated User instance

        Note:
            Password is automatically hashed by Django's set_password()
        """
        user.set_password(new_password)
        user.save()

        logger.info(
            "Password reset successful",
            extra={"extra_data": {"user_id": str(user.id)}}
        )

        return user

    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """
        Validate password strength

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message)

        Note:
            Customize validation rules as needed
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters"

        if password.isdigit():
            return False, "Password cannot be only numbers"

        if password.isalpha():
            return False, "Password must contain numbers"

        return True, ""
