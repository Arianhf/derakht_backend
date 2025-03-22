import phonenumbers
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from phonenumbers import parse as parse_phone_number
from rest_framework.exceptions import ValidationError
from django.conf import settings

from shop.models import BaseModel


class User(AbstractUser):
    email = models.EmailField(unique=True)
    age = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(150)],
        null=True,
    )
    profile_image = models.ImageField(
        upload_to="profile_images/", null=True, blank=True
    )
    phone_number = PhoneNumberField(
        null=True,
        blank=True,
        region="IR",
        error_messages={"invalid": "Please enter a valid Iranian phone number."},
    )
    is_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=255, null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name", "age"]

    def clean(self):
        super().clean()
        if self.phone_number:
            try:
                # Parse the phone number
                parsed_number = parse_phone_number(str(self.phone_number))

                # Check if it's a valid Iranian number (you can add more countries here later)
                allowed_regions = [
                    "IR"
                ]  # Add more country codes as needed, e.g., ['IR', 'US', 'GB']

                if parsed_number.country_code == 98:  # Iran's country code
                    # Validate Iranian number format
                    if not (
                        len(str(parsed_number.national_number)) == 10
                        and str(parsed_number.national_number).startswith("9")
                    ):
                        raise ValidationError(
                            {
                                "phone_number": "Iranian mobile numbers must start with 9 and be 10 digits long."
                            }
                        )
                else:
                    if str(parsed_number.country_code) not in [
                        str(phonenumbers.country_code_for_region(region))
                        for region in allowed_regions
                    ]:
                        raise ValidationError(
                            {
                                "phone_number": f'Phone numbers are only accepted from these regions: {", ".join(allowed_regions)}'
                            }
                        )

                # Ensure the number is valid for its region
                if not phonenumbers.is_valid_number(parsed_number):
                    raise ValidationError(
                        {
                            "phone_number": "This phone number is not valid for its region."
                        }
                    )

            except phonenumbers.phonenumberutil.NumberParseException:
                raise ValidationError(
                    {
                        "phone_number": "Please enter a valid phone number with country code."
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class Address(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
        verbose_name="User",
    )
    recipient_name = models.CharField("Recipient Name", max_length=255)
    address = models.TextField("Address")
    city = models.CharField("City", max_length=100)
    province = models.CharField("Province", max_length=100)
    postal_code = models.CharField("Postal Code", max_length=20)
    phone_number = models.CharField("Phone Number", max_length=15)
    is_default = models.BooleanField("Is Default", default=False)

    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.recipient_name} - {self.city}"

    def save(self, *args, **kwargs):
        # If this address is being set as default
        if self.is_default:
            # Get all other addresses for this user and set is_default to False
            Address.objects.filter(user=self.user, is_default=True).exclude(
                pk=self.pk
            ).update(is_default=False)

        # If this is the only address for the user, make it default
        if not Address.objects.filter(user=self.user).exists() and not self.is_default:
            self.is_default = True

        super().save(*args, **kwargs)
