# CLAUDE.md

## Project Overview
Django 5.1 REST API for Persian educational platform: story creation, Wagtail CMS blog, e-commerce with Zarinpal payments. Poetry + PostgreSQL + MinIO storage.

## Custom Commands
```bash
python manage.py init_feature_flags  # Required after fresh DB setup
```

## Critical Architecture Patterns

### BaseModel (ALL models inherit this)
```python
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)  # UUID PKs, not integers
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
```

### App-Specific Gotchas

**shop**
- Models split into modules: `product.py`, `order.py`, `cart.py`, `payment.py`, `invoice.py`
- Payment abstraction: `PaymentService.request_payment()` → `PaymentGatewayFactory.get_gateway()` → gateway impl
- Anonymous cart: Frontend sends `X-Anonymous-Cart-ID` header, DB constraint ensures `user` XOR `anonymous_id`
- Order statuses: CART → PENDING → PROCESSING → CONFIRMED → SHIPPED → DELIVERED
  - Also: AWAITING_VERIFICATION, CANCELLED, REFUNDED, RETURNED
  - Validate transitions via manager methods

**stories**
- Canvas-based JSON: `StoryPart.canvas_text_data`, `canvas_illustration_data`
- Template chain: `StoryTemplate` → `Story` → `StoryPart`
- Activity types: `WRITE_FOR_DRAWING`, `ILLUSTRATE`, `COMPLETE_STORY`
- Orientation: `LANDSCAPE`/`PORTRAIT`

**users**
- Email as `USERNAME_FIELD` (not username)
- Iranian phone validation
- Address auto-default selection

**core**
- Generic comments via ContentTypes: `content_type` + `object_id` + `GenericForeignKey`
- Feature flags: check `FeatureFlag` model before enabling features

**blog**
- Wagtail Page models: `BlogPost`, `BlogIndexPage`
- Jalali dates in serializers

### MinIO Storage Paths
- `stories/covers/`
- `product_images/`
- `profile_images/`
- `invoices/pdfs/`

### JWT Config
- Access: 60min, Refresh: 7 days (rotating + blacklist)
- Endpoints: `/api/users/login/`, `/api/users/token/refresh/`

### Zarinpal Payment Flow
1. `POST /api/shop/payments/request/{order_id}/` → creates Payment, returns redirect URL
2. User pays on Zarinpal → redirects to `ZARINPAL_CALLBACK_URL` with Authority
3. `POST /api/shop/payments/verify/` with Authority → verifies, updates order, creates invoice

### Wagtail CMS
- Admin: `/admin/` (Wagtail), `/django-admin/` (Django)
- API: `/api/blog/` (Wagtail API v2)

### Logging
```python
from core.logging_utils import get_logger
logger = get_logger(__name__)
logger.info("Message", extra={"extra_data": {"key": "value"}})
```
Files: `derakht.log`, `errors.log`, `security.log`, `performance.log`, `audit.log`, `analytics.log`

### Environment Variables (Critical)
```bash
# MinIO
MINIO_ENDPOINT=http://minio:9000
MINIO_EXTERNAL_API=127.0.0.1:9000

# Zarinpal
ZARINPAL_MERCHANT_ID=...
ZARINPAL_CALLBACK_URL=http://localhost:3000/payment/callback
ZARINPAL_SANDBOX=True

# Frontend
FRONTEND_URL=http://localhost:3000
CSRF_TRUSTED_ORIGINS=https://derrakht.ir,https://derakht.darkube.app
```

## API Routes
```
/api/users/     → registration, login, profile, addresses
/api/stories/   → CRUD, templates, canvas data, image uploads
/api/blog/      → Wagtail API v2
/api/shop/      → products, cart, orders, payments, invoices
/api/core/      → feature flags, comments, search
/admin/         → Wagtail CMS
/django-admin/  → Django admin
```

## Conventions (Project-Specific)

- **Persian errors**: All user-facing messages in Persian, code/comments in English
- **UUIDs everywhere**: All models inherit BaseModel → UUID PKs
- **Logging**: Always use `get_logger(__name__)` with `extra_data`, never print()
- **Service layer**: Complex logic in `services/`, views are thin controllers
- **Status transitions**: Validate order/payment status changes
- **N+1 queries**: `DatabaseQueryLoggingMiddleware` warns; use `select_related()`/`prefetch_related()`
- **Multi-serializers**: List (minimal), detail (full), write (validation) - use `get_serializer_class()`

## Git Convention
**CRITICAL**: NEVER mention co-authored-by, tool used for commits, or "Generated with..." in commit messages or PRs.
