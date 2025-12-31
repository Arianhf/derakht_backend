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

## Advanced Patterns and Conventions

### Django Signals Usage

Signals are used extensively in the shop app for automation (`shop/signals.py`):

**Order Item Changes** (`post_save` on `OrderItem`):
```python
@receiver(post_save, sender=OrderItem)
def update_order_total(sender, instance, created, **kwargs):
    instance.order.calculate_total()
    # Logs item creation/update with old/new totals
```

**Payment Completion** (`post_save` on `Payment`):
```python
@receiver(post_save, sender=Payment)
def handle_payment_status_change(sender, instance, **kwargs):
    if instance.status == "COMPLETED":
        # Auto-creates Invoice and InvoiceItems
        # Logs to payment_logger and audit_logger
```

**Order Status Tracking** (`pre_save` on `Order`):
```python
@receiver(pre_save, sender=Order)
def track_order_status_change(sender, instance, **kwargs):
    if old_order.status != instance.status:
        # Creates OrderStatusHistory record
        # Logs status change to audit
```

**Key principle**: Signals handle side effects and cross-cutting concerns. Keep signals focused on single responsibility.

### Custom Managers

**OrderManager** (`shop/managers.py`):
```python
class OrderManager(models.Manager):
    def get_active_cart(self, user):
        """Get or create user's cart"""
        cart, created = self.get_or_create(
            user=user, status=OrderStatus.CART,
            defaults={'currency': Currency.IRR}
        )
        return cart

    def get_user_orders(self, user):
        """Get completed orders (excludes carts)"""
        return self.filter(user=user).exclude(
            status=OrderStatus.CART
        ).order_by('-created_at')
```

**CartManager** (`shop/managers.py`):
```python
class CartManager(models.Manager):
    def get_or_create_cart(self, user=None):
        """Handle both authenticated and anonymous carts"""
        # Returns (cart, created) tuple

    def get_cart_total_items(self, cart):
        """Aggregate total items using Sum"""
        return cart.items.aggregate(total_items=Sum('quantity'))['total_items'] or 0
```

**Convention**: Use managers for common queries and business logic that relates to querysets, not individual instances.

### Serializer Patterns

**Multiple Serializers Per Model**: Different serializers for different use cases:

```python
# List view - minimal fields for performance
class ProductListSerializer(serializers.ModelSerializer):
    feature_image = serializers.SerializerMethodField()
    age_range = serializers.CharField(source="age_range", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "title", "price", "feature_image", "age_range", "slug"]

# Detail view - comprehensive fields
class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ["id", "title", "description", "price", "images", "meta_title", ...]

# Minimal for nested serialization
class ProductMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "title", "price", "feature_image"]
```

**Read vs Write Serializers**: Separate serializers for different operations:

```python
class StoryTemplateViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return StoryTemplateWriteSerializer  # Accepts file uploads, different validation
        return StoryTemplateSerializer  # Read-only, includes nested data
```

**SerializerMethodField for Computed Values**:
```python
class ProductSerializer(serializers.ModelSerializer):
    feature_image = serializers.SerializerMethodField()

    def get_feature_image(self, obj):
        if obj.feature_image and obj.feature_image.image:
            return obj.feature_image.image.get_rendition("original").url
        return None
```

**Nested Serializers**: Use for related data:
```python
class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)  # Nested read
    category_id = serializers.UUIDField(write_only=True)  # Write by ID
    images = ProductImageSerializer(many=True, read_only=True)
```

### View Patterns

**ViewSet Types Used**:
- `viewsets.ModelViewSet` - Full CRUD (stories, templates)
- `viewsets.ReadOnlyModelViewSet` - List + retrieve only (products, orders)
- `viewsets.ViewSet` - Custom actions only (cart)
- `viewsets.GenericViewSet` - Base for custom combinations (StoryPartViewSet)
- `APIView` - Low-level for payment callbacks

**Custom Actions with @action**:
```python
class StoryTemplateViewSet(viewsets.ModelViewSet):
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def start_story(self, request, pk=None):
        """Initialize a new story from template"""
        template = self.get_object()
        # Custom business logic
        return Response(serializer.data)
```

**Dynamic Permissions**:
```python
class StoryTemplateViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [IsStaffUser()]  # Write operations require staff
```

**Parser Classes for File Uploads**:
```python
class StoryTemplateViewSet(viewsets.ModelViewSet):
    parser_classes = [JSONParser, MultiPartParser, FormParser]
```

### Anonymous Cart Implementation

**Model Constraints** (`shop/models/cart.py`):
```python
class Cart(BaseModel):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    anonymous_id = models.UUIDField(null=True, blank=True, db_index=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False) | models.Q(anonymous_id__isnull=False),
                name="cart_must_have_user_or_anonymous_id"
            )
        ]
```

**View Logic** (`shop/views/cart.py`):
```python
def get_cart(self, request, anonymous_cart_id=None):
    # Authenticated users: use user FK
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(
            user=request.user, defaults={"anonymous_id": None}
        )
        return cart, created

    # Anonymous users: check header or generate new UUID
    if not anonymous_cart_id:
        header_cart_id = request.META.get("HTTP_X_ANONYMOUS_CART_ID")
        if header_cart_id:
            anonymous_cart_id = uuid.UUID(header_cart_id)

    if anonymous_cart_id:
        cart, created = Cart.objects.get_or_create(
            anonymous_id=anonymous_cart_id, user=None
        )
    else:
        cart = Cart.objects.create(anonymous_id=uuid.uuid4(), user=None)

    return cart, created
```

**Frontend Integration**: Frontend sends `X-Anonymous-Cart-ID` header with UUID for cart persistence.

### Error Handling Patterns

**Standardized Error Responses**:
```python
# 400 Bad Request
return Response(
    {"error": "پیام خطا به فارسی"},
    status=status.HTTP_400_BAD_REQUEST
)

# 404 Not Found - use get_object_or_404
order = get_object_or_404(Order, id=order_id, user=request.user)

# 403 Forbidden
log_security_event(
    "unauthorized_payment_access",
    "medium",
    f"User {request.user.id} attempted to access payment {payment_id}",
    ip_address=get_client_ip(request)
)
return Response(
    {"error": "شما مجاز به دسترسی به این پرداخت نیستید"},
    status=status.HTTP_403_FORBIDDEN
)
```

**Error Logging Pattern**:
```python
try:
    # Business logic
    result = PaymentService.request_payment(order, gateway_name)
except Exception as e:
    log_api_error(
        logger, e, request.path, request.method,
        user_id=request.user.id,
        request_data=request.data
    )
    return Response(
        {"error": "خطا در پردازش درخواست"},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
```

### Permission Patterns

**Custom Permission Classes** (`stories/permissions.py`):
```python
class IsStaffUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff
```

**Usage in Views**:
```python
# Class-level
class CartViewSet(viewsets.ViewSet):
    permission_classes = (permissions.AllowAny,)

# Dynamic per-action
class StoryTemplateViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [IsStaffUser()]

# Action-level override
@action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
def start_story(self, request, pk=None):
    pass
```

### Order Status Lifecycle

**Complete Status Flow** (`shop/choices.py`):

```
Order Statuses:
- CART              → Initial state (shopping cart)
- PENDING           → Order placed, awaiting payment
- AWAITING_VERIFICATION → Manual payment receipt uploaded, needs admin review
- PROCESSING        → Payment in progress (gateway callback received)
- CONFIRMED         → Payment completed, order confirmed
- SHIPPED           → Order dispatched
- DELIVERED         → Order completed successfully
- CANCELLED         → Order cancelled
- REFUNDED          → Payment refunded
- RETURNED          → Product returned

Payment Statuses:
- PENDING           → Payment initiated
- PROCESSING        → Gateway processing
- COMPLETED         → Payment successful
- FAILED            → Payment failed
- REFUNDED          → Payment refunded
- CANCELLED         → Payment cancelled

Valid Transitions (enforced by business logic):
CART → PENDING (checkout)
PENDING → PROCESSING (payment initiated)
PENDING → AWAITING_VERIFICATION (manual payment receipt uploaded)
AWAITING_VERIFICATION → CONFIRMED (admin approves)
PROCESSING → CONFIRMED (payment verified)
CONFIRMED → SHIPPED (fulfillment)
SHIPPED → DELIVERED (completion)
Any → CANCELLED (cancellation)
DELIVERED → RETURNED (return)
```

### Pagination

**Custom Pagination** (`stories/pagination.py`):
```python
class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10  # Default
    page_size_query_param = 'page_size'  # Client can override: ?page_size=25
    max_page_size = 100  # Prevent abuse
```

**Global Default** (`settings.py`):
```python
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}
```

### Performance Patterns

**Query Optimization**:
```python
# Use select_related for ForeignKey/OneToOne (single JOIN)
cart.items.select_related("product").all()

# Use prefetch_related for reverse ForeignKey/ManyToMany
Story.objects.prefetch_related("parts").all()

# Combine both
Order.objects.select_related("user").prefetch_related("items__product").all()
```

**N+1 Query Detection**: `DatabaseQueryLoggingMiddleware` logs warnings when:
- Query count > 50
- Total query time > 500ms
- Shows slowest queries in DEBUG mode

**Aggregation in Database**:
```python
# Good: Single query with aggregation
cart.items.aggregate(total_items=Sum('quantity'))['total_items'] or 0

# Bad: Fetch all and count in Python
sum([item.quantity for item in cart.items.all()])
```

### Code Quality and Formatting

**Black Formatter**: Configured in `pyproject.toml`
```bash
# Format all files
black .

# Check without modifying
black --check .

# Format specific app
black shop/ stories/
```

**Recommendations for Refactor**:
1. Add `flake8` for linting: `poetry add --dev flake8`
2. Add `isort` for import sorting: `poetry add --dev isort`
3. Set up pre-commit hooks:
   ```bash
   poetry add --dev pre-commit
   # Create .pre-commit-config.yaml with black, flake8, isort
   pre-commit install
   ```
4. Add `mypy` for type checking: `poetry add --dev mypy django-stubs`

### Testing Strategy

**Current State**: Test files exist but are empty (`# Create your tests here.`)

**Recommended Testing Structure**:

```python
# shop/tests/test_models.py
from django.test import TestCase
from shop.models import Product, Order

class ProductModelTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(...)

    def test_product_age_range(self):
        self.assertEqual(self.product.age_range, "5-10")

# shop/tests/test_views.py
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

class CartViewTests(APITestCase):
    def test_add_to_cart_authenticated(self):
        response = self.client.post('/api/shop/cart/add_item/', {...})
        self.assertEqual(response.status_code, 200)

# shop/tests/test_services.py
from django.test import TestCase
from shop.services.payment import PaymentService

class PaymentServiceTests(TestCase):
    def test_request_payment_creates_payment_record(self):
        result = PaymentService.request_payment(order)
        self.assertTrue(result['success'])
```

**Test Commands**:
```bash
# Run all tests
python manage.py test

# Run specific app
python manage.py test shop

# Run specific test class
python manage.py test shop.tests.test_models.ProductModelTests

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

**Fixtures**: Create fixtures for common test data:
```bash
python manage.py dumpdata shop.Product --indent 2 > shop/fixtures/products.json
```

### API Response Conventions

**Success Response**:
```json
{
  "id": "uuid",
  "field": "value",
  "nested": {...}
}
```

**List Response (Paginated)**:
```json
{
  "count": 42,
  "next": "http://api/endpoint/?page=2",
  "previous": null,
  "results": [...]
}
```

**Error Response**:
```json
{
  "error": "پیام خطا به فارسی",
  "detail": "Additional error details (optional)"
}
```

**Validation Error**:
```json
{
  "field_name": ["خطای اعتبارسنجی"],
  "another_field": ["خطای دیگر"]
}
```

**Status Codes Used**:
- `200 OK` - Successful GET, PUT, PATCH
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Validation errors, invalid data
- `401 Unauthorized` - Missing/invalid authentication
- `403 Forbidden` - Authenticated but lacks permission
- `404 Not Found` - Resource doesn't exist
- `500 Internal Server Error` - Server-side errors (logged)

## Key Files Reference

- `derakht/settings.py` - All Django configuration
- `derakht/urls.py` - Root URL routing
- `core/logging_utils.py` - Logging utilities and formatters
- `core/middleware.py` - Logging, analytics, and database performance middleware
- `shop/services/payment.py` - Payment service abstraction
- `shop/gateways/factory.py` - Payment gateway factory
- `shop/gateways/zarinpal_sdk.py` - Zarinpal integration
- `shop/models/base.py` - BaseModel abstract class
- `shop/managers.py` - Custom managers (OrderManager, CartManager)
- `shop/signals.py` - Django signals for order/payment automation
- `shop/choices.py` - Enums for order/payment statuses
- `shop/serializers/` - Multiple serializers per model pattern
- `shop/views/` - ViewSet patterns and custom actions
- `stories/permissions.py` - Custom permission classes
- `stories/pagination.py` - Custom pagination configuration
- `blog/storages.py` - MinIO storage backends
- `LOGGING.md` - Comprehensive logging documentation
