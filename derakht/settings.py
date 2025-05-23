"""
Django settings for derakht project.

Generated by 'django-admin startproject' using Django 5.1.2.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

import os
from datetime import timedelta
from pathlib import Path

from django.conf import settings

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "testkey")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = int(os.environ.get("DJANGO_DEBUG", 0))

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Application definition

INSTALLED_APPS = [
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "wagtail.contrib.sitemaps",
    "wagtail_modeladmin",
    "modelcluster",
    "taggit",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "blog",
    "stories",
    "shop",
    "storages",
    "phonenumber_field",
    "rest_framework_simplejwt",
    "users",
    "core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "stories.middleware.CSRFExemptMiddleware",
]

ROOT_URLCONF = "derakht.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "derakht.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB"),
        "USER": os.environ.get("POSTGRES_USER"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("POSTGRES_HOST"),
        "PORT": os.environ.get("POSTGRES_PORT"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
WAGTAILADMIN_BASE_URL = "http://localhost:8000/content_admin"
WAGTAIL_SITE_NAME = "درخت"
WAGTAIL_USAGE_COUNT_ENABLED = True
WAGTAILIMAGES_MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
WAGTAILDOCS_SERVE_METHOD = "direct"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

# Security settings
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_BROWSER_XSS_FILTER = True
# SECURE_CONTENT_TYPE_NOSNIFF = True
# X_FRAME_OPTIONS = 'DENY'
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# MinIO settings
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
STATICFILES_STORAGE = "storages.backends.s3boto3.S3StaticStorage"

# MinIO credentials and configuration
AWS_ACCESS_KEY_ID = os.environ.get("MINIO_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = os.environ.get("MINIO_SECRET_KEY")
AWS_S3_ENDPOINT_URL = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
AWS_S3_CUSTOM_DOMAIN = os.environ.get("MINIO_EXTERNAL_API", "127.0.0.1:9000")
AWS_S3_USE_SSL = False if AWS_S3_ENDPOINT_URL.startswith("http://") else True
AWS_S3_VERIFY = False
AWS_DEFAULT_ACL = "public-read"
AWS_QUERYSTRING_AUTH = False
AWS_S3_FILE_OVERWRITE = False

# Static and media specific settings
AWS_STORAGE_BUCKET_NAME = os.environ.get("MINIO_BUCKET_NAME", "derakht")  # Add default
AWS_STATIC_BUCKET_NAME = os.environ.get("MINIO_STATIC_BUCKET_NAME", "static")
AWS_MEDIA_BUCKET_NAME = os.environ.get("MINIO_MEDIA_BUCKET_NAME", "media")

STORAGES = {
    "default": {
        "BACKEND": "blog.storages.MediaStorage",
    },
    "staticfiles": {
        "BACKEND": "blog.storages.StaticStorage",
    },
}

# URLs
STATIC_URL = f"{AWS_S3_CUSTOM_DOMAIN}/static/"
MEDIA_URL = f"{AWS_S3_CUSTOM_DOMAIN}/media/"

# Fallback locations
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

AUTH_USER_MODEL = "users.User"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Email settings (configure according to your email provider)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_PORT = os.environ.get("EMAIL_PORT")
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL")

# Frontend URL for email verification and password reset
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# Add these settings
WAGTAILSITEMAPS_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours (in seconds)

# Optional but recommended sitemap settings
WAGTAILSITEMAPS_SITE_URL = "https://derrakht.ir"
WAGTAILAPI_LIMIT_MAX = 50  # Max number of items per page in API responses


# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://derrakht.ir",
    "https://derrakht.ir",
]

csrf_trusted_origins_str = os.environ.get(
    "CSRF_TRUSTED_ORIGINS", "https://derrakht.ir,https://derakht.darkube.app"
)
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in csrf_trusted_origins_str.split(",")
]


CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-anonymous-cart-id",
]

# Add these settings to your settings.py file

# Payment settings
DEFAULT_PAYMENT_GATEWAY = "zarinpal_sdk"

AVAILABLE_PAYMENT_METHODS = [
    {
        "id": "zarinpal_sdk",
        "name": "Zarinpal (SDK)",
        "description": "پرداخت آنلاین با درگاه زرین‌پال (نسخه SDK)",
        "icon": "/static/img/payment/zarinpal.png",
        "enabled": True,
    },
]

# Zarinpal settings
# Zarinpal settings
ZARINPAL_MERCHANT_ID = os.environ.get(
    "ZARINPAL_MERCHANT_ID", "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
)
ZARINPAL_ACCESS_TOKEN = os.environ.get("ZARINPAL_ACCESS_TOKEN", "")  # For SDK version
ZARINPAL_CALLBACK_URL = os.environ.get("ZARINPAL_CALLBACK_URL", "http://localhost:8000")
ZARINPAL_SANDBOX = os.environ.get("ZARINPAL_SANDBOX", "True").lower() == "true"
try:
    from .local_settings import *
except ImportError:
    pass
