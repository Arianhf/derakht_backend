"""
Django settings for testing environment.
Optimized for fast, isolated test execution.
"""

from .settings import *  # noqa: F403

# Override settings for testing

# SECURITY WARNING: Use a static secret key for testing
SECRET_KEY = "test-secret-key-for-testing-only-do-not-use-in-production"

# Debug should be False in tests to catch production-like issues
DEBUG = False

# Test database configuration
# Use PostgreSQL for tests to match production behavior
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("TEST_DB_NAME", default="test_derakht"),
        "USER": env("TEST_DB_USER", default="postgres"),
        "PASSWORD": env("TEST_DB_PASSWORD", default="postgres"),
        "HOST": env("TEST_DB_HOST", default="localhost"),
        "PORT": env("TEST_DB_PORT", default="5432"),
        # Test-specific optimizations
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": 0,  # Don't pool connections in tests
        "TEST": {
            "NAME": "test_derakht",
            "SERIALIZE": False,  # Faster parallel test execution
            "CHARSET": "UTF8",
        },
    }
}

# Password hashers - use fast hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Email backend - use in-memory backend for tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# File storage - use in-memory storage for tests
DEFAULT_FILE_STORAGE = "django.core.files.storage.InMemoryStorage"
MEDIA_ROOT = "/tmp/test_media"
MEDIA_URL = "/test_media/"

# Static files
STATIC_ROOT = "/tmp/test_static"

# Disable migrations for faster test setup
# Use --no-migrations flag in pytest.ini instead
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __getitem__(self, item):
#         return None
# MIGRATION_MODULES = DisableMigrations()

# Logging - reduce verbosity in tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",  # Set to DEBUG to see SQL queries
            "propagate": False,
        },
    },
}

# Cache - use dummy cache for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# Celery/Django-tasks - use eager execution for tests
# CELERY_TASK_ALWAYS_EAGER = True
# CELERY_TASK_EAGER_PROPAGATES = True

# JWT settings - shorter tokens for faster tests
SIMPLE_JWT = {
    **SIMPLE_JWT,  # noqa: F405
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),  # noqa: F405
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=1),  # noqa: F405
}

# CORS - allow all origins in tests
CORS_ALLOW_ALL_ORIGINS = True

# CSRF - disable for API tests
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# MinIO/S3 - use local storage for tests
# Override in individual tests if needed
AWS_S3_ENDPOINT_URL = None
AWS_STORAGE_BUCKET_NAME = "test-bucket"

# Payment Gateway - use sandbox/mock mode
ZARINPAL_MERCHANT_ID = "test-merchant-id"
ZARINPAL_ACCESS_TOKEN = "test-access-token"
ZARINPAL_SANDBOX = True

# Frontend URL for testing
FRONTEND_URL = "http://localhost:3000"

# Wagtail settings for tests
WAGTAIL_SITE_NAME = "Derakht Test Site"

# Disable SSL redirect in tests
SECURE_SSL_REDIRECT = False

# Allowed hosts for tests
ALLOWED_HOSTS = ["*"]

# REST Framework settings for tests
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "TEST_REQUEST_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}
