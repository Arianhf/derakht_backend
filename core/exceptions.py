"""
Custom exception handlers for standardized error responses.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from core.logging_utils import get_logger

logger = get_logger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns consistent error format:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "پیام خطا به فارسی",
            "details": {}  # Optional additional context
        }
    }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Standardize the error format
        error_data = {
            "error": {
                "code": get_error_code(exc),
                "message": get_error_message(response.data),
                "details": get_error_details(response.data),
            }
        }
        response.data = error_data
    else:
        # Handle non-DRF exceptions
        logger.error(
            "Unhandled exception",
            extra={"extra_data": {
                "exception": str(exc),
                "type": type(exc).__name__,
            }}
        )

        response = Response(
            {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "خطای سرور. لطفا بعدا تلاش کنید",
                    "details": {},
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response


def get_error_code(exc):
    """Extract error code from exception"""
    # Map exception types to error codes
    error_codes = {
        'ValidationError': 'VALIDATION_ERROR',
        'PermissionDenied': 'PERMISSION_DENIED',
        'NotAuthenticated': 'NOT_AUTHENTICATED',
        'NotFound': 'NOT_FOUND',
        'MethodNotAllowed': 'METHOD_NOT_ALLOWED',
        'ParseError': 'PARSE_ERROR',
        'AuthenticationFailed': 'AUTHENTICATION_FAILED',
        'Throttled': 'THROTTLED',
        'UnsupportedMediaType': 'UNSUPPORTED_MEDIA_TYPE',
    }
    return error_codes.get(type(exc).__name__, 'UNKNOWN_ERROR')


def get_error_message(data):
    """Extract user-friendly message from error data"""
    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])
        # Return first error message found
        for value in data.values():
            if isinstance(value, list) and value:
                return str(value[0])
            elif isinstance(value, str):
                return value
    elif isinstance(data, list) and data:
        return str(data[0])
    elif isinstance(data, str):
        return data

    return "خطایی رخ داده است"


def get_error_details(data):
    """Extract additional error details"""
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k != 'detail'}
    return {}
