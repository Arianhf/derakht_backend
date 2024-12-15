from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from phonenumber_field.modelfields import PhoneNumberField
from phonenumbers import parse as parse_phone_number
import phonenumbers
from rest_framework.exceptions import ValidationError


class User(AbstractUser):
    email = models.EmailField(unique=True)
    age = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(150)],
        null=True,
    )
    profile_image = models.ImageField(
        upload_to='profile_images/',
        null=True,
        blank=True
    )
    phone_number = PhoneNumberField(
        null=True,
        blank=True,
        region='IR',
        error_messages={
            'invalid': 'Please enter a valid Iranian phone number.'
        }
    )
    is_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=255, null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'age']

    def clean(self):
        super().clean()
        if self.phone_number:
            try:
                # Parse the phone number
                parsed_number = parse_phone_number(str(self.phone_number))

                # Check if it's a valid Iranian number (you can add more countries here later)
                allowed_regions = ['IR']  # Add more country codes as needed, e.g., ['IR', 'US', 'GB']

                if parsed_number.country_code == 98:  # Iran's country code
                    # Validate Iranian number format
                    if not (len(str(parsed_number.national_number)) == 10 and
                            str(parsed_number.national_number).startswith('9')):
                        raise ValidationError({
                            'phone_number': 'Iranian mobile numbers must start with 9 and be 10 digits long.'
                        })
                else:
                    if str(parsed_number.country_code) not in [str(phonenumbers.country_code_for_region(region))
                                                               for region in allowed_regions]:
                        raise ValidationError({
                            'phone_number': f'Phone numbers are only accepted from these regions: {", ".join(allowed_regions)}'
                        })

                # Ensure the number is valid for its region
                if not phonenumbers.is_valid_number(parsed_number):
                    raise ValidationError({
                        'phone_number': 'This phone number is not valid for its region.'
                    })

            except phonenumbers.phonenumberutil.NumberParseException:
                raise ValidationError({
                    'phone_number': 'Please enter a valid phone number with country code.'
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

    def __str__(self):
        return self.email
