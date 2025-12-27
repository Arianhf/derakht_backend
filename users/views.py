from datetime import datetime, timedelta
import logging

import jwt
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from core.logging_utils import (
    get_logger,
    log_user_action,
    log_analytics_event,
    log_security_event,
    get_client_ip,
)
from stories.models import ImageAsset
from stories.serializers import ImageAssetSerializer
from users.models import User
from users.serializers import CustomTokenObtainPairSerializer, SignUpSerializer
from .models import Address
from .serializers import (
    UserSerializer,
    AddressSerializer,
    UserLoginSerializer,
    UserRegistrationSerializer,
    ProfileImageSerializer,
)

# Initialize loggers
logger = get_logger("users")
auth_logger = get_logger("users.auth")
audit_logger = get_logger("audit")


class UserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get current user information"""
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        """Update user profile"""
        serializer = UserSerializer(request.user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()

            logger.info(
                f"User profile updated: {request.user.id}",
                extra={
                    "extra_data": {
                        "user_id": request.user.id,
                        "updated_fields": list(request.data.keys()),
                    }
                },
            )

            log_user_action(
                audit_logger,
                "profile_updated",
                user_id=request.user.id,
                user_email=request.user.email,
                extra_data={"updated_fields": list(request.data.keys())},
            )

            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileImageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Upload or update profile image"""
        serializer = ProfileImageSerializer(
            request.user,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Profile image uploaded successfully",
                    "profile_image": serializer.data.get('profile_image')
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """Delete profile image"""
        user = request.user
        if user.profile_image:
            user.profile_image.delete(save=True)
            return Response(
                {"message": "Profile image deleted successfully"},
                status=status.HTTP_200_OK
            )
        return Response(
            {"error": "No profile image to delete"},
            status=status.HTTP_400_BAD_REQUEST
        )


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def set_default(self, request, pk=None):
        """Set an address as default"""
        address = self.get_object()
        address.is_default = True
        address.save()
        return Response(AddressSerializer(address).data)


class AuthView(APIView):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=["post"])
    def login(self, request):
        """User login"""
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            password = serializer.validated_data["password"]
            user = authenticate(request, email=email, password=password)

            if user:
                refresh = RefreshToken.for_user(user)

                auth_logger.info(
                    f"User login successful: {user.email}",
                    extra={
                        "extra_data": {
                            "user_id": user.id,
                            "email": user.email,
                            "ip_address": get_client_ip(request),
                        }
                    },
                )

                log_user_action(
                    audit_logger,
                    "user_login",
                    user_id=user.id,
                    user_email=user.email,
                    extra_data={"ip_address": get_client_ip(request)},
                )

                log_analytics_event(
                    "user_login",
                    "users",
                    user_id=user.id,
                    properties={"ip_address": get_client_ip(request)},
                )

                return Response(
                    {
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                        "user": UserSerializer(user).data,
                    }
                )

            # Log failed login attempt
            log_security_event(
                "auth_failure",
                "medium",
                f"Failed login attempt for email: {email}",
                ip_address=get_client_ip(request),
                extra_data={"email": email},
            )

            return Response(
                {"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def signup(self, request):
        """User registration"""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            auth_logger.info(
                f"New user registered: {user.email}",
                extra={
                    "extra_data": {
                        "user_id": user.id,
                        "email": user.email,
                        "ip_address": get_client_ip(request),
                    }
                },
            )

            log_user_action(
                audit_logger,
                "user_registered",
                user_id=user.id,
                user_email=user.email,
                extra_data={"ip_address": get_client_ip(request)},
            )

            log_analytics_event(
                "user_registered",
                "users",
                user_id=user.id,
                properties={"ip_address": get_client_ip(request)},
            )

            return Response(
                {
                    "user": UserSerializer(user).data,
                    "message": "User registered successfully",
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@method_decorator(csrf_exempt, name="dispatch")
class SignUpView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = SignUpSerializer
    authentication_classes = []

    def perform_create(self, serializer):
        user = serializer.save()
        # Generate verification token
        token = default_token_generator.make_token(user)
        user.email_verification_token = token
        user.save()

        # TODO: add this part.
        # Send verification email
        # verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}&email={user.email}"
        # send_mail(
        #     'Verify your email',
        #     f'Please click this link to verify your email: {verification_url}',
        #     settings.DEFAULT_FROM_EMAIL,
        #     [user.email],
        #     fail_silently=False,
        # )


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_email(request):
    email = request.data.get("email")
    token = request.data.get("token")

    try:
        user = User.objects.get(email=email, email_verification_token=token)
        user.is_verified = True
        user.email_verification_token = None
        user.save()
        return Response({"message": "Email verified successfully"})
    except User.DoesNotExist:
        return Response(
            {"error": "Invalid verification link"}, status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def request_password_reset(request):
    email = request.data.get("email")
    try:
        user = User.objects.get(email=email)
        token = jwt.encode(
            {"user_id": str(user.id), "exp": datetime.utcnow() + timedelta(hours=24)},
            settings.SECRET_KEY,
            algorithm="HS256",
        )

        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        send_mail(
            "Reset your password",
            f"Click this link to reset your password: {reset_url}",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return Response({"message": "Password reset email sent"})
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
    token = request.data.get("token")
    new_password = request.data.get("new_password")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user = User.objects.get(id=payload["user_id"])
        user.set_password(new_password)
        user.save()
        return Response({"message": "Password reset successfully"})
    except (jwt.ExpiredSignatureError, jwt.DecodeError, User.DoesNotExist):
        return Response(
            {"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST
        )


class UserAssetViewSet(viewsets.ModelViewSet):
    """ViewSet for managing user assets (images)"""
    serializer_class = ImageAssetSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return assets for the user specified in the URL"""
        user_id = self.kwargs.get('user_id')
        # Only allow users to access their own assets
        if str(self.request.user.id) != user_id:
            return ImageAsset.objects.none()
        return ImageAsset.objects.filter(uploaded_by=self.request.user).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        """List user assets with pagination"""
        queryset = self.filter_queryset(self.get_queryset())

        # Get pagination params
        page = request.query_params.get('page', 1)
        limit = request.query_params.get('limit', 10)

        # Use DRF's built-in pagination
        page_obj = self.paginate_queryset(queryset)
        if page_obj is not None:
            serializer = self.get_serializer(page_obj, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Upload a new asset"""
        user_id = self.kwargs.get('user_id')

        # Verify user can only upload to their own account
        if str(request.user.id) != user_id:
            return Response(
                {"error": "You can only upload assets to your own account"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(uploaded_by=request.user)

        # Return the created asset with id and file URL
        return Response(
            {
                "id": str(serializer.instance.id),
                "file": serializer.instance.file.url,
                "created_at": serializer.instance.created_at
            },
            status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        """Delete an asset"""
        user_id = self.kwargs.get('user_id')

        # Verify user can only delete their own assets
        if str(request.user.id) != user_id:
            return Response(
                {"error": "You can only delete your own assets"},
                status=status.HTTP_403_FORBIDDEN
            )

        instance = self.get_object()

        # Verify the asset belongs to the user
        if instance.uploaded_by != request.user:
            return Response(
                {"error": "You can only delete your own assets"},
                status=status.HTTP_403_FORBIDDEN
            )

        self.perform_destroy(instance)
        return Response(
            {"message": "Asset deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )
