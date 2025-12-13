"""
Factory Boy factories for users app models.
"""

import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model

from users.models import Address

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """
    Factory for creating User instances.
    """

    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Faker("name")
    phone_number = "+989123456789"
    age = factory.Faker("random_int", min=18, max=80)
    is_active = True
    email_verified = False

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        """Set password for the user."""
        if create:
            obj.set_password(extracted or "testpass123")
            obj.save()

    @factory.post_generation
    def with_address(obj, create, extracted, **kwargs):
        """
        Create addresses for the user.
        Usage: UserFactory(with_address=2)  # Creates 2 addresses
        """
        if create and extracted:
            count = extracted if isinstance(extracted, int) else 1
            for i in range(count):
                AddressFactory(user=obj, is_default=(i == 0))


class AddressFactory(DjangoModelFactory):
    """
    Factory for creating Address instances.
    """

    class Meta:
        model = Address

    user = factory.SubFactory(UserFactory)
    recipient_name = factory.Faker("name")
    address = factory.Faker("street_address")
    city = factory.Faker("city")
    province = factory.Faker("state")
    postal_code = factory.Faker("postcode")
    phone_number = "+989123456789"
    is_default = False
    is_active = True


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def create_user_with_addresses(address_count=2, **user_kwargs):
    """
    Helper to create a user with multiple addresses.

    Usage:
        user = create_user_with_addresses(address_count=3, email="custom@example.com")
    """
    user = UserFactory(**user_kwargs)

    for i in range(address_count):
        AddressFactory(user=user, is_default=(i == 0))

    return user


def create_verified_user(**kwargs):
    """
    Helper to create an email-verified user.

    Usage:
        user = create_verified_user(email="verified@example.com")
    """
    return UserFactory(email_verified=True, **kwargs)
