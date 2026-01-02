# users/validators.py
from django.core.exceptions import ValidationError
import re


def validate_iranian_phone(value: str) -> str:
    """
    Validate and normalize Iranian phone number format.

    Accepts formats:
    - 09123456789
    - +989123456789
    - 9123456789

    Args:
        value: Phone number string to validate

    Returns:
        Normalized phone number (09XXXXXXXXX format)

    Raises:
        ValidationError: If phone number format is invalid

    Examples:
        >>> validate_iranian_phone("09123456789")
        "09123456789"
        >>> validate_iranian_phone("+989123456789")
        "09123456789"
        >>> validate_iranian_phone("9123456789")
        "09123456789"
    """
    if not value:
        return value

    # Remove spaces and dashes
    phone = value.replace(' ', '').replace('-', '')

    # Pattern 1: 09123456789 (standard format)
    pattern1 = re.compile(r'^09\d{9}$')
    # Pattern 2: +989123456789 (international format)
    pattern2 = re.compile(r'^\+989\d{9}$')
    # Pattern 3: 9123456789 (without leading zero)
    pattern3 = re.compile(r'^9\d{9}$')

    if pattern1.match(phone):
        return phone
    elif pattern2.match(phone):
        # Convert +989... to 09...
        return '0' + phone[3:]
    elif pattern3.match(phone):
        # Convert 9... to 09...
        return '0' + phone
    else:
        raise ValidationError(
            'شماره تلفن باید به فرمت 09123456789 باشد',
            code='invalid_phone_format'
        )


def validate_iranian_postal_code(value: str) -> str:
    """
    Validate Iranian postal code format.

    Iranian postal codes are 10 digits without any separator.

    Args:
        value: Postal code string to validate

    Returns:
        Normalized postal code (10 digits)

    Raises:
        ValidationError: If postal code format is invalid

    Examples:
        >>> validate_iranian_postal_code("1234567890")
        "1234567890"
        >>> validate_iranian_postal_code("1234-56789")  # Will normalize
        "123456789"
    """
    if not value:
        return value

    # Remove spaces and dashes
    postal_code = value.replace(' ', '').replace('-', '')

    # Pattern: exactly 10 digits
    pattern = re.compile(r'^\d{10}$')

    if pattern.match(postal_code):
        return postal_code
    else:
        raise ValidationError(
            'کد پستی باید ۱۰ رقم باشد',
            code='invalid_postal_code'
        )


def validate_national_code(value: str) -> str:
    """
    Validate Iranian national code (کد ملی) format and check digit.

    Iranian national codes are 10 digits with a check digit validation.

    Args:
        value: National code string to validate

    Returns:
        Normalized national code (10 digits)

    Raises:
        ValidationError: If national code format or check digit is invalid

    Note:
        This implements the standard Iranian national code validation algorithm.
    """
    if not value:
        return value

    # Remove spaces and dashes
    national_code = value.replace(' ', '').replace('-', '')

    # Must be exactly 10 digits
    if not re.match(r'^\d{10}$', national_code):
        raise ValidationError(
            'کد ملی باید ۱۰ رقم باشد',
            code='invalid_national_code_format'
        )

    # Check for invalid patterns (all same digit)
    if len(set(national_code)) == 1:
        raise ValidationError(
            'کد ملی نامعتبر است',
            code='invalid_national_code'
        )

    # Validate check digit
    check_digit = int(national_code[9])
    sum_digits = sum(int(national_code[i]) * (10 - i) for i in range(9))
    remainder = sum_digits % 11

    if (remainder < 2 and check_digit == remainder) or \
       (remainder >= 2 and check_digit == 11 - remainder):
        return national_code
    else:
        raise ValidationError(
            'کد ملی نامعتبر است',
            code='invalid_national_code_checksum'
        )
