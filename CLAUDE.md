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
python manage.py dbshell

# Create superuser
python manage.py createsuperuser

# Initialize feature flags
python manage.py init_feature_flags

# Testing
python manage.py test
python manage.py test shop.tests.PaymentTestCase

# Django shell
python manage.py shell
```

### Docker

```bash
# Development with hot reload
docker-compose -f docker-compose.dev.yml up

# Production build
docker-compose up -d

# Run management commands in container
docker-compose exec web python manage.py migrate
```

## Architecture Overview

### Django Apps Structure

**blog** - Wagtail CMS integration for blog content
- Extends Wagtail's Page model (`BlogPost`, `BlogIndexPage`)
- Rich text editing with Persian (Jalali) date support
- API exposed via Wagtail API v2 router at `/api/blog/`
- SEO metadata, schema markup, Open Graph tags

**shop** - E-commerce with payment gateway integration
- Models split into modules: `product.py`, `order.py`, `cart.py`, `payment.py`, `invoice.py`
- Payment abstraction via service layer (`services/payment.py`) and gateway factory pattern
- Anonymous cart support via UUID in headers/cookies
- Order status state machine with validation

**stories** - Interactive story creation platform
- Canvas-based JSON storage (`StoryPart.canvas_text_data`, `canvas_illustration_data`)
- Template instantiation system (`StoryTemplate` → `Story` → `StoryPart`)
- Activity types: `WRITE_FOR_DRAWING`, `ILLUSTRATE`, `COMPLETE_STORY`
- Orientation (`LANDSCAPE`/`PORTRAIT`) and size support

**users** - Custom user model with JWT authentication
- Email-based authentication (email as `USERNAME_FIELD`)
- Iranian phone number validation
- Address management with automatic default selection
- Author/SEO fields for blog attribution

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

**Payment Service Layer**
```
PaymentRequestView → PaymentService.request_payment()
                  → PaymentGatewayFactory.get_gateway("zarinpal_sdk")
                  → ZarinpalSDKGateway.request_payment()
```
Payment logic abstracted from views. Gateways implement `BasePaymentGateway` interface.

**Generic Comments via ContentTypes**
```python
content_type = ForeignKey(ContentType)
object_id = UUIDField()
content_object = GenericForeignKey('content_type', 'object_id')
```

### File Storage (MinIO/S3)

Uses `django-storages` with S3-compatible MinIO backend. Upload paths:
- `stories/covers/` - Story cover images
- `product_images/` - Product photos
- `profile_images/` - User avatars
- `invoices/pdfs/` - Generated invoices

Configure via `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_ENDPOINT`, `MINIO_EXTERNAL_API` environment variables.

### Authentication (JWT)

Uses `djangorestframework-simplejwt`:
- Access tokens: 60 minutes
- Refresh tokens: 7 days, rotating with blacklist
- Endpoints: `/api/users/login/`, `/api/users/token/refresh/`
- Header: `Authorization: Bearer <access_token>`

### Payment Integration (Zarinpal)

**Flow**:
1. Frontend: `POST /api/shop/payments/request/{order_id}/`
2. Backend: Creates `Payment` record, calls Zarinpal SDK, returns redirect URL
3. User: Completes payment on Zarinpal
4. Zarinpal: Redirects to `ZARINPAL_CALLBACK_URL` with Authority
5. Frontend: `POST /api/shop/payments/verify/` with Authority
6. Backend: Verifies with Zarinpal, updates order status, creates invoice

Configure via `ZARINPAL_MERCHANT_ID`, `ZARINPAL_ACCESS_TOKEN`, `ZARINPAL_CALLBACK_URL`, `ZARINPAL_SANDBOX` environment variables.

### Wagtail CMS Integration

- Admin: `/admin/` (Wagtail), `/django-admin/` (Django)
- API: Wagtail API v2 router at `/api/blog/`
- Page models extend `wagtail.models.Page`
- Custom serializers for `RichTextField`, Jalali dates

### Logging System

See `LOGGING.md` for comprehensive documentation.

**Log files**: `derakht.log`, `errors.log`, `security.log`, `performance.log`, `audit.log`, `analytics.log`

**Usage**:
```python
from core.logging_utils import get_logger
logger = get_logger(__name__)
logger.info("Message", extra={"extra_data": {"key": "value"}})
```

### Environment Variables

Required in `.env` file:

```bash
# Django core
DJANGO_SECRET_KEY=your_secret_key
DJANGO_DEBUG=1
DJANGO_LOG_LEVEL=INFO

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

# Payment (Zarinpal)
ZARINPAL_MERCHANT_ID=XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
ZARINPAL_ACCESS_TOKEN=your_token
ZARINPAL_CALLBACK_URL=http://localhost:3000/payment/callback
ZARINPAL_SANDBOX=True

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
```

## Important Conventions

- **Persian Text**: All user-facing messages in Persian, code/comments in English
- **UUIDs**: All models inherit `BaseModel` with UUID primary keys
- **Logging**: Use `get_logger(__name__)` with `extra_data` for context
- **Service Layer**: Complex logic in `services/`, views are thin controllers
- **Status Transitions**: Validate all order/payment status changes
- **Query Optimization**: Always use `select_related()`/`prefetch_related()`

## Common Development Tasks

### Adding a New API Endpoint

1. Define model in `<app>/models.py`
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

Set `DJANGO_LOG_LEVEL=DEBUG` for verbose output.

### Testing Payment Flow Locally

1. Set `ZARINPAL_SANDBOX=True` in `.env`
2. Create order via `/api/shop/orders/`
3. Request payment via `/api/shop/payments/request/{order_id}/`
4. Zarinpal sandbox auto-approves test payments
5. Verify via `/api/shop/payments/verify/`

## Technology Stack

- **Framework**: Django 5.1, Django REST Framework 3.15
- **CMS**: Wagtail 6.2
- **Database**: PostgreSQL
- **Storage**: MinIO/S3 (django-storages, boto3)
- **Authentication**: djangorestframework-simplejwt 5.3
- **Payment**: zarinpal-py-sdk 0.1.0
- **Dependency management**: Poetry
- **WSGI server**: Gunicorn 23.0 (production)

## Advanced Patterns

### Custom Managers

Use managers for common queries and business logic (e.g., `OrderManager.get_active_cart()`). Keep manager methods focused and reusable.

### Serializer Patterns

Use multiple serializers per model: list (minimal), detail (comprehensive), write (validation).

```python
def get_serializer_class(self):
    if self.action in ['create', 'update', 'partial_update']:
        return WriteSerializer
    return ReadSerializer
```

### View Patterns

**ViewSet Types**: `ModelViewSet` (full CRUD), `ReadOnlyModelViewSet` (list/retrieve), `GenericViewSet` (custom), `APIView` (low-level)

**Custom Actions**:
```python
@action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
def start_story(self, request, pk=None):
    # Custom business logic
    return Response(data)
```

### Anonymous Cart

Cart supports authenticated users (via `user` FK) and anonymous users (via `anonymous_id` UUID). Frontend sends `X-Anonymous-Cart-ID` header. Database constraint ensures one or the other is set.

### Error Handling

Return Persian error messages with appropriate status codes. Use `get_object_or_404()` for lookups. Log exceptions before returning 500 errors.

### Order Status Lifecycle

**Statuses**: CART → PENDING → PROCESSING → CONFIRMED → SHIPPED → DELIVERED

**Also**: AWAITING_VERIFICATION (manual payment), CANCELLED, REFUNDED, RETURNED

Validate transitions using manager methods or signals.

### Performance Patterns

Use `select_related()` for ForeignKey/OneToOne, `prefetch_related()` for reverse FK/M2M. Aggregate in database, not Python. `DatabaseQueryLoggingMiddleware` warns on N+1 queries.

### Testing

```bash
python manage.py test                    # Run all tests
python manage.py test shop               # Specific app
```

Tests in `<app>/tests/test_*.py`. Use `TestCase` with `setUp()` for fixtures.

## Key Files Reference

- `derakht/settings.py` - Django configuration
- `derakht/urls.py` - Root URL routing
- `core/logging_utils.py` - Logging utilities
- `core/middleware.py` - Logging and performance middleware
- `shop/services/payment.py` - Payment service abstraction
- `shop/gateways/` - Payment gateway implementations
- `shop/models/base.py` - BaseModel abstract class
- `shop/managers.py` - Custom managers
- `shop/signals.py` - Django signals
- `shop/choices.py` - Enums for statuses
- `LOGGING.md` - Comprehensive logging documentation


##‌ Git
NEVER ever mention a co-authored-by or similar aspects. In particular, never mention the tool used to create the commit message or PR.

