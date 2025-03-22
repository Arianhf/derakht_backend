from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Address

User = get_user_model()
# users/serializers.py


class SmallUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "age", "profile_image")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "age",
            "profile_image",
            "phone_number",
            "is_verified",
        )
        read_only_fields = ("is_verified",)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "password",
            "confirm_password",
            "age",
            "profile_image",
            "phone_number",
        )

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match")
        try:
            validate_password(attrs["password"])
        except ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        user = User.objects.create_user(
            username=validated_data["email"],  # Using email as username
            **validated_data,
        )
        return user


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id",
            "recipient_name",
            "address",
            "city",
            "province",
            "postal_code",
            "phone_number",
            "is_default",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["user"] = user
        return super().create(validated_data)


class UserSerializer(serializers.ModelSerializer):
    default_address = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "default_address",
        ]
        read_only_fields = ["id", "email"]

    def get_default_address(self, obj):
        default_address = obj.addresses.filter(is_default=True).first()
        if default_address:
            return AddressSerializer(default_address).data
        return None


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(style={"input_type": "password"}, write_only=True)


class UserRegistrationSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(
        style={"input_type": "password"}, write_only=True
    )

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "confirm_password",
            "first_name",
            "last_name",
            "phone_number",
            "age",
        ]
        extra_kwargs = {"password": {"write_only": True}, "age": {"required": False}}

    def validate(self, data):
        if data["password"] != data.pop("confirm_password"):
            raise serializers.ValidationError("Passwords do not match")
        return data

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
