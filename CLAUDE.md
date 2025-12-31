# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Derakht Backend** is a Django 5.1 REST API backend for a Persian-language educational platform featuring interactive story creation, blog/CMS content, and e-commerce functionality. Built with Django REST Framework, Wagtail CMS, PostgreSQL, and MinIO (S3-compatible) storage.

## Core Commands

### Development

```bash
# Install dependencies (using Poetry)
poetry install
poetry shell

# Run development server
python manage.py runserver

# Database operations
python manage.py makemigrations
python manage.py migrate
python manage.py dbshell  # PostgreSQL shell access

# Create superuser
python manage.py createsuperuser

# Initialize feature flags
python manage.py init_feature_flags

# Collect static files
python manage.py collectstatic --noinput

# Django shell
python manage.py shell
```

### Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test stories
python manage.py test shop.tests.PaymentTestCase

# Run with verbosity
python manage.py test --verbosity=2
```

### Docker

```bash
# Development with hot reload
docker-compose -f docker-compose.dev.yml up

# Production build
docker-compose up -d

# View logs
docker-compose logs -f web

# Run management commands in container
docker-compose exec web python manage.py migrate
```

## Architecture Overview

### Django Apps Structure

**blog** - Wagtail CMS integration for blog content
- Extends Wagtail's Page model (`BlogPost`, `BlogIndexPage`)
- Rich text editing with Persian (Jalali) date support
- API exposed via Wagtail API v2 router
- SEO metadata, schema markup, Open Graph tags

**shop** - E-commerce with payment gateway integration
- Models split into modules: `product.py`, `order.py`, `cart.py`, `payment.py`, `invoice.py`
- Payment abstraction via service layer (`services/payment.py`) and gateway factory pattern
- Anonymous cart support via UUID in headers/cookies
- Order status state machine with validation

**stories** - Interactive story creation platform
- Canvas-based JSON storage for text and illustrations (`StoryPart.canvas_text_data`, `canvas_illustration_data`)
- Template instantiation system (`StoryTemplate` → `Story` → `StoryPart`)
- Activity types: `WRITE_FOR_DRAWING`, `ILLUSTRATE`, `COMPLETE_STORY`
- Orientation (`LANDSCAPE`/`PORTRAIT`) and size (`20x20`, `25x25`, `15x23`) support

**users** - Custom user model with JWT authentication
- Email-based authentication (email as `USERNAME_FIELD`)
- Iranian phone number validation with custom validators
- Address management with automatic default selection
- Author/SEO fields (bio, social links) for blog attribution

**core** - Shared utilities and cross-cutting concerns
- `FeatureFlag` model for feature toggles
- `Comment` model using Django ContentTypes for generic relations
- Comprehensive logging utilities (`logging_utils.py`)
- Global search functionality

### Key Architectural Patterns

**BaseModel Abstract Class**
```python
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
```
All shop models inherit from `BaseModel` for consistent UUID-based primary keys.

**Payment Service Layer**
```
PaymentRequestView → PaymentService.request_payment()
                  → PaymentGatewayFactory.get_gateway("zarinpal_sdk")
                  → ZarinpalSDKGateway.request_payment()
```
Payment logic abstracted from views. Gateways implement `BasePaymentGateway` interface.

**Order Status State Machine**
Order status transitions validated through business logic:
- `CART` → `PENDING` (checkout)
- `PENDING` → `PROCESSING` (payment confirmed)
- `PROCESSING` → `CONFIRMED` (order confirmed)
- `CONFIRMED` → `SHIPPED` → `DELIVERED`

Invalid transitions raise exceptions.

**Generic Comments via ContentTypes**
`Comment` model uses Django's ContentTypes framework to attach comments to any model:
```python
content_type = ForeignKey(ContentType)
object_id = UUIDField()
content_object = GenericForeignKey('content_type', 'object_id')
```

### File Storage (MinIO/S3)

Uses `django-storages` with S3-compatible MinIO backend:
- **Buckets**: Configured via `MINIO_BUCKET_NAME`, `MINIO_STATIC_BUCKET_NAME`, `MINIO_MEDIA_BUCKET_NAME`
- **Custom storage classes**: `blog.storages.MediaStorage`, `blog.storages.StaticStorage`
- **Upload paths**:
  - `stories/covers/` - Story cover images
  - `story_templates/covers/` - Template covers
  - `image_assets/` - User-uploaded illustrations
  - `product_images/` - Product photos
  - `profile_images/` - User avatars
  - `invoices/pdfs/` - Generated invoices

Configure via environment:
```bash
MINIO_ACCESS_KEY=<access_key>
MINIO_SECRET_KEY=<secret_key>
MINIO_ENDPOINT=http://minio:9000
MINIO_EXTERNAL_API=127.0.0.1:9000  # Public URL for file access
```

### Authentication (JWT)

Uses `djangorestframework-simplejwt`:
- **Access tokens**: 60 minutes lifetime
- **Refresh tokens**: 7 days, rotating with blacklist
- **Endpoints**:
  - `POST /api/users/login/` - Obtain token pair
  - `POST /api/users/token/refresh/` - Refresh access token
- **Header format**: `Authorization: Bearer <access_token>`

### Payment Integration (Zarinpal)

**Configuration**:
```bash
ZARINPAL_MERCHANT_ID=XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
ZARINPAL_ACCESS_TOKEN=<token>
ZARINPAL_CALLBACK_URL=http://localhost:3000/payment/callback
ZARINPAL_SANDBOX=True  # Use sandbox for development
```

**Payment Flow**:
1. Frontend: `POST /api/shop/payments/request/{order_id}/`
2. Backend: Creates `Payment` record, calls Zarinpal SDK
3. Backend: Returns redirect URL
4. User: Completes payment on Zarinpal
5. Zarinpal: Redirects to `ZARINPAL_CALLBACK_URL` with Authority
6. Frontend: `POST /api/shop/payments/verify/` with Authority
7. Backend: Verifies with Zarinpal, updates order status, creates invoice

**Service abstraction**: All payment logic in `shop/services/payment.py`, gateway implementations in `shop/gateways/`.

### Wagtail CMS Integration

- **Admin interfaces**: `/admin/` (Wagtail), `/django-admin/` (Django)
- **API**: Wagtail API v2 router at `/api/blog/`
- **Page models**: `BlogPost`, `BlogIndexPage` extend `wagtail.models.Page`
- **Rich text**: Custom serializers handle Wagtail's `RichTextField` for API responses
- **Jalali dates**: Custom `JalaliDatePanel` for Persian calendar in admin
- **Images**: `ProductImage` references Wagtail's `Image` model with foreign keys

### Logging System

Comprehensive logging documented in `LOGGING.md`. Key points:

**Log files** (in `logs/` directory):
- `derakht.log` - General application logs
- `errors.log` - Error-level only
- `security.log` - Auth failures, suspicious activity
- `performance.log` - Slow requests (>1000ms)
- `audit.log` - User actions, compliance
- `analytics.log` - User behavior (JSON format)

**Utilities** (`core/logging_utils.py`):
```python
from core.logging_utils import (
    get_logger,
    log_performance,
    log_user_action,
    log_analytics_event,
    log_security_event,
)

logger = get_logger(__name__)
logger.info("Message", extra={"extra_data": {"key": "value"}})

@log_performance("operation_name")
def my_function():
    pass
```

**Middleware** (auto-configured in `settings.py`):
- `RequestLoggingMiddleware` - Logs all HTTP requests with duration, IP, user agent
- `UserContextMiddleware` - Adds user context to log records
- `AnalyticsMiddleware` - Tracks API endpoint usage
- `DatabaseQueryLoggingMiddleware` - Monitors query count/time (DEBUG mode)

**Log level**: Set via `DJANGO_LOG_LEVEL` environment variable (DEBUG, INFO, WARNING, ERROR, CRITICAL).

### Environment Variables

Required in `.env` file:

```bash
# Django core
DJANGO_SECRET_KEY=your_secret_key
DJANGO_DEBUG=1  # 0 for production
DJANGO_LOG_LEVEL=INFO
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database
POSTGRES_DB=derakht
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_HOST=db
POSTGRES_PORT=5432

# MinIO/S3
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_ENDPOINT=http://minio:9000
MINIO_EXTERNAL_API=127.0.0.1:9000
MINIO_BUCKET_NAME=derakht
MINIO_STATIC_BUCKET_NAME=static
MINIO_MEDIA_BUCKET_NAME=media

# Payment (Zarinpal)
ZARINPAL_MERCHANT_ID=XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
ZARINPAL_ACCESS_TOKEN=your_token
ZARINPAL_CALLBACK_URL=http://localhost:3000/payment/callback
ZARINPAL_SANDBOX=True

# Email (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_password
DEFAULT_FROM_EMAIL=noreply@derrakht.ir

# Frontend
FRONTEND_URL=http://localhost:3000
CSRF_TRUSTED_ORIGINS=https://derrakht.ir,https://derakht.darkube.app
```

## URL Routing Structure

```
/api/users/          → User registration, login, profile, addresses
/api/stories/        → Story CRUD, templates, canvas data, image uploads
/api/blog/           → Wagtail API v2 (blog posts, pages)
/api/shop/           → Products, cart, orders, payments, invoices
/api/core/           → Feature flags, comments, search
/admin/              → Wagtail CMS admin
/django-admin/       → Django admin
/sitemap.xml         → Wagtail sitemap
/robots.txt          → SEO robots file
```

## Important Conventions

### Persian Text
All user-facing messages, error responses, and content are in Persian. Code comments and variable names remain in English.

### UUID Primary Keys
All models inherit `BaseModel` or explicitly use `UUIDField` for primary keys. Never use auto-incrementing integers for user-facing IDs.

### Logging Best Practices
- Use `get_logger(__name__)` for all modules
- Include structured context via `extra={"extra_data": {...}}`
- Log user actions to `audit` logger for compliance
- Performance-critical operations use `@log_performance` decorator
- Security events use `log_security_event()` with severity levels

### Service Layer for Business Logic
Complex operations (payments, order processing) go in `services/` modules, not views. Views should be thin controllers.

### Wagtail Serializers
When exposing Wagtail models via API, use custom serializers from `blog/serializers.py`:
- `RichTextField` → Custom serializer for HTML rendering
- `JalaliDateField` → Persian calendar dates
- `CommaSeparatedListField` → Tag lists

### Status Transitions
Order/Payment status changes must be validated. Use manager methods or signals to enforce business rules, not direct field updates.

## Common Development Tasks

### Adding a New API Endpoint

1. Define model in `<app>/models.py` (or `<app>/models/<module>.py` for split models)
2. Create serializer in `<app>/serializers.py`
3. Create view/viewset in `<app>/views.py`
4. Register route in `<app>/urls.py`
5. Run migrations: `python manage.py makemigrations && python manage.py migrate`
6. Add logging using `core.logging_utils`

### Debugging with Logs

Check appropriate log file in `logs/`:
- General issues: `derakht.log`
- Errors: `errors.log`
- Auth problems: `security.log`
- Slow performance: `performance.log`
- User action timeline: `audit.log`

Set `DJANGO_LOG_LEVEL=DEBUG` for verbose output during development.

### Testing Payment Flow Locally

1. Set `ZARINPAL_SANDBOX=True` in `.env`
2. Use test merchant ID from Zarinpal documentation
3. Create order via `/api/shop/orders/`
4. Request payment via `/api/shop/payments/request/{order_id}/`
5. Zarinpal sandbox auto-approves test payments
6. Verify via `/api/shop/payments/verify/` with returned Authority

### Database Queries

Access PostgreSQL directly:
```bash
python manage.py dbshell
# Or in Docker:
docker-compose exec db psql -U postgres -d derakht
```

Check for N+1 queries in DEBUG mode - `DatabaseQueryLoggingMiddleware` logs when query count exceeds 50.

## Technology Stack

- **Framework**: Django 5.1, Django REST Framework 3.15
- **CMS**: Wagtail 6.2, wagtail-modeladmin 2.0
- **Database**: PostgreSQL (via psycopg2-binary)
- **Storage**: MinIO/S3 (django-storages, boto3)
- **Authentication**: djangorestframework-simplejwt 5.3
- **Payment**: zarinpal-py-sdk 0.1.0
- **Persian dates**: jdatetime 5.0
- **Phone validation**: django-phonenumber-field 8.0
- **CORS**: django-cors-headers 4.6
- **Dependency management**: Poetry
- **WSGI server**: Gunicorn 23.0 (production)

## Key Files Reference

- `derakht/settings.py` - All Django configuration
- `derakht/urls.py` - Root URL routing
- `core/logging_utils.py` - Logging utilities and formatters
- `core/middleware.py` - Logging, analytics, and database performance middleware
- `shop/services/payment.py` - Payment service abstraction
- `shop/gateways/factory.py` - Payment gateway factory
- `shop/gateways/zarinpal_sdk.py` - Zarinpal integration
- `shop/models/base.py` - BaseModel abstract class
- `blog/storages.py` - MinIO storage backends
- `LOGGING.md` - Comprehensive logging documentation
