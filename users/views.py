from datetime import datetime, timedelta

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
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from users.models import User
from users.serializers import CustomTokenObtainPairSerializer, SignUpSerializer
from .models import Address
from .serializers import (
    UserSerializer,
    AddressSerializer,
    UserLoginSerializer,
    UserRegistrationSerializer,
)


class UserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get current user information"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        """Update user profile"""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
                return Response(
                    {
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                        "user": UserSerializer(user).data,
                    }
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
