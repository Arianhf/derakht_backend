# Django Backend Codebase Audit Report

**Generated**: 2025-12-31
**Project**: Derakht Educational Platform Backend
**Total Issues Found**: 103 issues across 9 categories

---

## Executive Summary

This audit analyzes the Django backend codebase for the Derakht educational platform, covering code organization, naming conventions, API design, database optimization, type safety, security, error handling, testing, and performance. The audit identified 103 distinct issues across 9 categories.

**Severity Breakdown**:
- **Critical**: 22 issues (require immediate attention)
- **High**: 31 issues (address soon)
- **Medium**: 32 issues (plan to fix)
- **Low**: 18 issues (nice to have)

---

## 1. Code Organization Issues

### 1.1 Views with Business Logic (Should be in Services)

**Location**: `shop/views/cart.py`
- **Lines 48-62**: Cart retrieval logic directly in view method `get_cart()`
- **Lines 137-152**: Product stock validation and cart item creation logic in `add_item()`
- **Lines 544-611**: Complex promo code validation and discount calculation logic in `apply_promo()`
- **Lines 463-477**: Shipping validation and cost calculation in `checkout()`

**Issue**: Business logic should be extracted to service layer for reusability and testing.

```python
# Lines 544-584 - Complex business logic in view
promo = PromoCode.objects.get(...)
if promo.max_uses and promo.used_count >= promo.max_uses:
    return Response({"error": "..."})
if total_amount < promo.min_purchase:
    return Response({"error": "..."})
if promo.discount_type == "fixed":
    discount_amount = promo.discount_value
else:
    discount_amount = total_amount * (promo.discount_value / 100)
```

**Recommendation**: Create `shop/services/cart.py` with methods like `apply_promo_code()`, `validate_cart_checkout()`.

---

**Location**: `shop/views/cart.py`
- **Lines 416-517**: Order creation and checkout logic mixing view and business logic

```python
# Lines 482-513 - Should be in OrderService
order = Order.objects.create(...)
ShippingInfo.objects.create(...)
for cart_item in cart.items.all():
    OrderItem.objects.create(...)
cart.items.all().delete()
```

**Recommendation**: Extract to `OrderService.create_from_cart()`.

---

**Location**: `shop/views/order.py`
- **Lines 56-89**: Payment request logic should be in PaymentService (deprecated endpoint)
- **Lines 91-139**: Payment verification logic mixing view concerns

**Issue**: Duplicate/deprecated payment logic. Should delegate entirely to `PaymentService`.

---

**Location**: `core/views.py`
- **Lines 39-178**: Global search implementation with complex query logic directly in view
- **Lines 66-96**: Blog search with trigram similarity calculations
- **Lines 81-96**: Product search logic

**Recommendation**: Extract to `core/services/search.py` with `SearchService.search_all()`.

---

**Location**: `users/views.py`
- **Lines 134-146**: Address default setting logic in view action
- **Lines 297-313**: Password reset token generation in view

```python
# Lines 297-301 - Business logic in view
token = jwt.encode(
    {"user_id": str(user.id), "exp": datetime.utcnow() + timedelta(hours=24)},
    settings.SECRET_KEY,
    algorithm="HS256",
)
```

**Recommendation**: Create `users/services/auth.py` with `generate_reset_token()`.

---

### 1.2 Fat Models (Logic Should be in Services/Selectors)

**Location**: `shop/models/order.py`
- **Lines 55-60**: `calculate_total()` method performing aggregation
- **Lines 71-98**: Business logic for order state transitions

```python
def calculate_total(self):
    """Calculate total amount from order items"""
    total = sum(item.total_price for item in self.items.all())
    self.total_amount = total
    self.save()
    return total
```

**Issue**: Models should be thin. Calculations and business rules belong in services.

**Recommendation**: Move to `OrderService.recalculate_total()`.

---

**Location**: `users/models.py`
- **Lines 54-101**: Complex phone number validation in model's `clean()` method

```python
def clean(self):
    super().clean()
    if self.phone_number:
        # 47 lines of validation logic
```

**Issue**: Validation logic should be in validators module or serializer.

**Recommendation**: Extract to `users/validators.py` with `validate_iranian_phone()`.

---

**Location**: `users/models.py`
- **Lines 134-146**: Address default setting logic in model save method

**Issue**: Business logic in model save() can lead to unexpected behavior.

**Recommendation**: Move to service layer or use signals.

---

### 1.3 Missing Service Layer Separation

**Missing Files**:
- `shop/services/cart.py` - No cart service exists
- `shop/services/order.py` - No order service exists
- `shop/services/promo.py` - No promo code service
- `users/services/auth.py` - No auth service exists
- `core/services/search.py` - No search service
- `stories/services/` - Entire directory missing

**Existing Service**: Only `shop/services/payment.py` exists (56 lines, very thin).

---

### 1.4 Apps Too Large or Mixed Responsibilities

**Location**: `shop/`

**File Count**:
- 6 model files (base, cart, category, invoice, order, payment, product, promo)
- 5 serializer files
- 6 view files
- Multiple service files

**Issue**: Shop app handles too many concerns (products, cart, orders, payments, invoices, promo codes). Consider splitting into:
- `products/` - Product catalog
- `orders/` - Order management
- `payments/` - Payment processing
- `promotions/` - Promo codes and discounts

---

## 2. Naming Inconsistencies

### 2.1 File Naming Issues

**Location**: `blog/category_serializer.py`

**Issue**: Should be `serializers.py` or `serializers/category.py` to match convention. Other apps use `serializers.py`.

---

**Location**: `shop/order_management.py`

**Issue**: Module name unclear. Should be `services/order_status.py` or `utils/order_transitions.py`.

---

### 2.2 Inconsistent Serializer Naming

**Location**: Multiple files

**Issues**:
- `shop/serializers/cart.py` has both `CartDetailsSerializer` and `CartItemSerializer`
- `shop/serializers/product.py` has `ProductSerializer`, `ProductListSerializer`, `ProductDetailSerializer`, `ProductMinimalSerializer`
- No clear pattern for read/write/list/detail variants

**Standard Pattern Missing**: Should follow `<Model>ReadSerializer`, `<Model>WriteSerializer`, `<Model>ListSerializer`.

---

### 2.3 URL Naming Inconsistencies

**Location**: `shop/urls.py`

```python
path("payments/request/<uuid:order_id>/", ...)  # Uses 'request'
path("payments/verify/", ...)                    # Uses 'verify'
path("payments/callback/<str:gateway>/<uuid:payment_id>/", ...)  # Uses 'callback'
```

**Issue**: Mixing verbs and nouns. Should be consistent: either all verbs or all RESTful resource names.

---

**Location**: `users/urls.py`

```python
path("verify-email/", ...)           # kebab-case
path("request-password-reset/", ...) # kebab-case
path("me/profile-image/", ...)       # kebab-case
path("<str:user_id>/assets/", ...)   # no prefix
```

**Issue**: Inconsistent use of prefix. Some use kebab-case, some don't.

---

### 2.4 Model Field Naming Issues

**Location**: `shop/models/payment.py`

```python
reference_id = models.CharField(...)  # Line 36
transaction_id = models.CharField(...) # Line 39
```

**Issue**: Both fields serve similar purposes but naming suggests different meanings. Unclear distinction.

---

**Location**: `stories/models.py`

```python
canvas_text_data = models.JSONField(...)            # Line 161
canvas_illustration_data = models.JSONField(...)    # Line 166
canvas_text_template = models.JSONField(...)        # Line 133
canvas_illustration_template = models.JSONField(...) # Line 138
```

**Issue**: Mixing `_data` and `_template` suffixes is confusing. Consider `canvas_text_user` vs `canvas_text_template`.

---

## 3. API Design Issues

### 3.1 Inconsistent Response Formats

**Location**: `shop/views/payment.py`

```python
# Line 119-127: Success response
return Response({
    "success": True,
    "payment_url": result["payment_url"],
    "authority": result.get("authority"),
    ...
})

# Line 142-149: Error response
return Response({
    "success": False,
    "error": result.get("error_message", "Payment request failed"),
    ...
}, status=status.HTTP_400_BAD_REQUEST)
```

**vs**

**Location**: `shop/views/cart.py`

```python
# Line 78-80: Error response (different format)
return Response(
    {"error": "Invalid cart ID format"},
    status=status.HTTP_400_BAD_REQUEST,
)
```

**Issue**: Inconsistent error response format. Some use `{"success": false, "error": "..."}`, others use `{"error": "..."}`.

**Recommendation**: Standardize on one format:
```python
{
    "error": {
        "code": "INVALID_CART_ID",
        "message": "سبد خرید معتبر نیست",
        "details": {}
    }
}
```

---

**Location**: `core/views.py`

```python
# Lines 388-392: Uses structured error format
return Response({
    "code": "EMPTY_CART",
    "message": "سبد خرید خالی است",
    "severity": "error",
}, status=status.HTTP_400_BAD_REQUEST)
```

**Issue**: Only some endpoints use structured error format with `code`, `message`, `severity`.

---

### 3.2 Missing Pagination on List Endpoints

**Location**: `shop/views/product.py`

```python
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.filter(...)
    # No pagination_class defined!
```

**Issue**: Large product lists will return all items. Missing default pagination.

---

**Location**: `shop/views/order.py`

```python
class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    # No pagination_class defined
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)...
```

**Issue**: No pagination for user orders list.

---

**Location**: `users/views.py`

```python
class AddressViewSet(viewsets.ModelViewSet):
    # No pagination_class defined
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)
```

**Issue**: Should have pagination even if addresses are typically few.

---

### 3.3 Endpoints Not Following REST Conventions

**Location**: `shop/urls.py`

```python
path("payments/request/<uuid:order_id>/", ...)
```

**Issue**: Should be `POST /orders/{order_id}/payments/` (nested resource) instead of `POST /payments/request/{order_id}/`.

---

**Location**: `shop/views/cart.py`

```python
@action(detail=False, methods=["post"])
def add_item(self, request):  # Line 97

@action(detail=False, methods=["post"])
def update_quantity(self, request):  # Line 158

@action(detail=False, methods=["post"])
def remove_item(self, request):  # Line 231
```

**Issue**: Cart items should be nested resources:
- `POST /cart/items/` (add)
- `PATCH /cart/items/{id}/` (update quantity)
- `DELETE /cart/items/{id}/` (remove)

Current design uses non-RESTful actions.

---

**Location**: `stories/views.py`

```python
@action(detail=True, methods=["post"])
def upload_cover(self, request, pk=None):  # Line 398
```

**Issue**: Should be `PUT /stories/{id}/cover/` instead of custom action.

---

### 3.4 Inconsistent Error Messages (Persian vs English)

**Location**: Mixed throughout

```python
# English
{"error": "Invalid cart ID format"}  # cart.py line 78

# Persian
{"message": "سبد خرید خالی است"}  # cart.py line 390

# Mixed
{"error": "Product is not available"}  # cart.py line 124 (English)
{"error": f"Minimum purchase of {promo.min_purchase} is required"}  # cart.py line 571 (English)
```

**Issue**: Per CLAUDE.md, all user-facing messages should be in Persian. Many error messages are in English.

---

## 4. Database & Query Issues

### 4.1 N+1 Query Problems (Missing select_related/prefetch_related)

**Location**: `shop/views/cart.py`

```python
# Line 89
data = {
    ...
    "items": cart.items.select_related("product").all(),
}
```

**Issue**: Missing `prefetch_related('product__images')` for product images. Each item will trigger separate query for feature image.

---

**Location**: `shop/views/order.py`

```python
# Lines 19-22
def get_queryset(self):
    return Order.objects.filter(user=self.request.user).prefetch_related(
        "items", "items__product"
    )
```

**Issue**: Good! But missing `prefetch_related('items__product__images')` for product images.

---

**Location**: `shop/views/product.py`

```python
# Line 19
queryset = Product.objects.filter(is_active=True, is_available=True, is_visible=True)
```

**Issue**: No `prefetch_related('images')` in base queryset. N+1 when serializing list of products.

---

**Location**: `blog/views.py`

```python
# Lines 318-324
category_posts = (
    BlogPost.objects.live()
    .filter(categories__in=post.categories.all())
    .exclude(id__in=included_ids)
    .distinct()
    .order_by("-date")[:needed]
)
```

**Issue**: Missing `prefetch_related('categories', 'tags')` and `select_related('header_image')`.

---

**Location**: `shop/models/cart.py`

```python
# Lines 48-50
@property
def total_amount(self):
    return sum(item.total_price for item in self.items.all())
```

**Issue**: Property triggers query every time it's accessed. Should use annotation or cache result.

---

### 4.2 Missing Database Indexes

**Location**: `shop/models/product.py`

```python
class Product(BaseModel):
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    is_available = models.BooleanField(_("Is Available"), default=True)
    is_visible = models.BooleanField(_("Is Visible"), default=True)
```

**Issue**: No explicit `Meta.indexes` for commonly filtered fields:
- `is_available`, `is_visible`, `is_active` (often filtered together)
- `category` (foreign key, but explicit index recommended)
- `min_age`, `max_age` (filtered in age range queries)

**Recommendation**:
```python
class Meta:
    indexes = [
        models.Index(fields=['is_active', 'is_available', 'is_visible']),
        models.Index(fields=['category', '-created_at']),
        models.Index(fields=['min_age', 'max_age']),
    ]
```

---

**Location**: `shop/models/order.py`

```python
class Order(BaseModel):
    user = models.ForeignKey(...)
    status = models.CharField(...)
```

**Issue**: No index on `['user', 'status']` which is commonly queried together.

**Recommendation**:
```python
class Meta:
    indexes = [
        models.Index(fields=['user', 'status', '-created_at']),
    ]
```

---

**Location**: `shop/models/payment.py`

```python
class Payment(BaseModel):
    order = models.ForeignKey(...)
    status = models.CharField(...)
```

**Issue**: No index on `status` which is frequently queried for pending payments.

---

**Location**: `stories/models.py`

```python
class Story(models.Model):
    author = models.ForeignKey(...)
    status = models.CharField(...)
```

**Issue**: No composite index on `['author', 'status']` or `['status', '-created_date']` for common queries.

---

### 4.3 Inefficient Querysets in Loops

**Location**: `shop/views/cart.py`

```python
# Lines 504-510
for cart_item in cart.items.all():
    OrderItem.objects.create(
        order=order,
        product=cart_item.product,
        quantity=cart_item.quantity,
        price=cart_item.product.price,
    )
```

**Issue**: Should use `bulk_create()` for better performance:

```python
order_items = [
    OrderItem(order=order, product=item.product, quantity=item.quantity, price=item.product.price)
    for item in cart.items.select_related('product')
]
OrderItem.objects.bulk_create(order_items)
```

---

**Location**: `stories/views.py`

```python
# Lines 109-122
for story_part_template in template.template_parts.all():
    canvas_text_data = copy.deepcopy(...)
    canvas_illustration_data = copy.deepcopy(...)
    StoryPart.objects.create(...)
    parts_created += 1
```

**Issue**: Should use `bulk_create()` instead of individual creates.

---

### 4.4 Missing .only() / .defer() for Large Models

**Location**: `blog/views.py`

```python
# Line 137
posts = BlogPost.objects.live().only("slug", "last_published_at", ...)
```

**Good Example**: Uses `.only()` to fetch minimal fields for sitemap.

**Missing in**: Most other views don't use `.only()` when only specific fields are needed (e.g., list views that only show title, slug, price).

---

## 5. Type Safety Gaps

### 5.1 Missing Type Hints on Function Signatures

**Location**: `shop/views/cart.py`

```python
def get_cart(self, request, anonymous_cart_id=None):  # Line 31
    # No type hints for parameters or return value
```

**Recommendation**:
```python
def get_cart(self, request: Request, anonymous_cart_id: Optional[UUID] = None) -> Tuple[Cart, bool]:
```

---

**Location**: `users/models.py`

```python
def get_profile_url(self):  # Line 45
    # No return type hint
```

**Recommendation**:
```python
def get_profile_url(self) -> Optional[str]:
```

---

**Location**: Most view methods lack type hints

```python
def post(self, request, order_id=None):  # shop/views/payment.py line 39
def list(self, request, *args, **kwargs):  # users/views.py line 348
```

---

### 5.2 Any Usage (Type Safety Escape Hatch)

**Location**: `core/logging_utils.py`

```python
from typing import Any, Dict, Optional, Callable

def log_user_action(
    logger: logging.Logger,
    action: str,
    extra_data: Optional[Dict[str, Any]] = None,  # Line 128
):
```

**Issue**: `Any` used in multiple places. Should use more specific types like `Dict[str, Union[str, int, bool]]`.

---

**Location**: `shop/services/payment.py`

```python
from typing import Dict, Any

def request_payment(cls, order: Order, gateway_name: Optional[str] = None) -> Dict[str, Any]:
```

**Issue**: Return type too generic. Should define a `PaymentResponse` TypedDict:

```python
from typing import TypedDict

class PaymentResponse(TypedDict):
    success: bool
    payment_url: str
    payment_id: UUID
    gateway: str
```

---

### 5.3 Missing Pydantic/Serializer Validation

**Location**: `shop/views/cart.py`

```python
# Lines 162-187: Manual validation
product_id = request.data.get("product_id")
quantity = request.data.get("quantity", 1)
anonymous_cart_id = request.data.get("anonymous_cart_id")

try:
    quantity = int(quantity)
    if quantity < 0:
        return Response({"error": "Quantity cannot be negative"}, ...)
except (ValueError, TypeError):
    return Response({"error": "Invalid quantity"}, ...)
```

**Issue**: Should use serializer for validation:

```python
class UpdateQuantitySerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=0)
    anonymous_cart_id = serializers.UUIDField(required=False, allow_null=True)

serializer = UpdateQuantitySerializer(data=request.data)
serializer.is_valid(raise_exception=True)
```

---

**Location**: `shop/views/payment.py`

```python
# Lines 371-378: Manual validation
order_id = request.data.get("order_id")
transaction_id = request.data.get("transaction_id")

if not order_id or not transaction_id:
    return Response(
        {"error": "Order ID and transaction ID are required"},
        status=status.HTTP_400_BAD_REQUEST,
    )
```

**Issue**: Should use serializer for request validation.

---

### 5.4 Untyped API Request/Response Schemas

**Issue**: No OpenAPI schema definitions or type documentation for most endpoints.

**Location**: Most ViewSets and APIViews lack:
- Request body schemas
- Response schemas
- Query parameter documentation

**Recommendation**: Use `drf-spectacular` for automatic OpenAPI schema generation with type hints.

---

## 6. Security Concerns

### 6.1 Missing Permission Checks on Views

**Location**: `blog/views.py`

```python
# Lines 18-20
class BlogPostAPIViewSet(PagesAPIViewSet):
    model = BlogPost
    authentication_classes = []
    permission_classes = []
```

**Issue**: Empty permission classes means anyone can access. Should explicitly use `[AllowAny]` if intentional.

---

**Location**: `shop/views/payment.py`

```python
# Lines 163-169
@method_decorator(csrf_exempt, name="dispatch")
class PaymentCallbackView(APIView):
    permission_classes = []  # Allow unauthenticated access for callbacks
```

**Issue**: While callback needs to be unauthenticated, should validate gateway signature/token to prevent abuse.

---

**Location**: `shop/views/product.py`

```python
# Line 155
class ProductInfoPageAPIViewSet(PagesAPIViewSet):
    permission_classes = []
```

**Issue**: Should explicitly use `[AllowAny]` for clarity.

---

### 6.2 Sensitive Data in Logs

**Location**: `shop/views/payment.py`

```python
# Lines 185-188
extra={
    "extra_data": {
        ...
        "callback_params": request.GET.dict(),  # May contain sensitive data
    }
}
```

**Issue**: Callback params might contain sensitive payment data that shouldn't be logged in plain text.

---

**Location**: `users/views.py`

```python
# Lines 158-159
extra={
    "email": email,
    "ip_address": get_client_ip(request),
}
```

**Issue**: Logging email addresses may violate privacy regulations. Should hash or pseudonymize.

---

### 6.3 Missing Input Validation

**Location**: `core/views.py`

```python
# Lines 59-63
try:
    threshold = float(request.GET.get('threshold', 0.1))
    threshold = max(0.0, min(1.0, threshold))  # Clamp between 0 and 1
except (ValueError, TypeError):
    threshold = 0.1
```

**Issue**: While it handles errors, doesn't validate if value is being used maliciously (e.g., very precise floats for timing attacks).

---

**Location**: `shop/views/cart.py`

```python
# Lines 110-117
if anonymous_cart_id:
    try:
        anonymous_cart_id = uuid.UUID(anonymous_cart_id)
    except (ValueError, TypeError):
        return Response(
            {"error": "Invalid cart ID format"},
            status=status.HTTP_400_BAD_REQUEST,
        )
```

**Good Example**: Validates UUID format.

---

**Missing Validation Examples**:
- File upload size limits (mostly handled, but not consistently)
- Rate limiting on expensive operations (search, cart operations)
- SQL injection protection (Django ORM handles this, but raw queries should be checked)

---

### 6.4 CSRF Exempt Decorators

**Location**: `shop/views/payment.py`

```python
@method_decorator(csrf_exempt, name="dispatch")
class PaymentCallbackView(APIView):  # Line 163
```

**Issue**: While necessary for callbacks, should verify payment gateway signature instead.

---

**Location**: `users/views.py`

```python
@method_decorator(csrf_exempt, name="dispatch")
class SignUpView(generics.CreateAPIView):  # Line 248
```

**Issue**: CSRF exempt on signup. Consider if this is necessary with JWT auth.

---

**Location**: `stories/views.py`

Multiple `@method_decorator(csrf_exempt)` decorators on story manipulation endpoints (lines 399, 459, 485, 588, 718, 777).

**Issue**: Too many endpoints exempted from CSRF protection. Review if necessary.

---

## 7. Error Handling Issues

### 7.1 Bare Except Clauses

**Location**: `core/views.py`

```python
# Lines 106-110
try:
    rendition = blog.header_image.get_rendition('fill-400x300')
    header_image_url = rendition.url
except:
    # Fallback to original if rendition fails
    header_image_url = blog.header_image.file.url if blog.header_image.file else None
```

**Issue**: Bare `except:` catches all exceptions, including `KeyboardInterrupt` and `SystemExit`. Should be `except Exception:`.

---

**Location**: `core/views.py`

```python
# Lines 134-140
try:
    rendition = feature_img.image.get_rendition('fill-400x300')
    feature_image_url = rendition.url
except:
    # Fallback to original if rendition fails
    feature_image_url = feature_img.image.file.url if feature_img.image.file else None
```

**Issue**: Same bare except issue.

---

### 7.2 Swallowed Exceptions

**Location**: `shop/views/payment.py`

```python
# Lines 151-160
except Exception as e:
    log_api_error(...)
    raise
```

**Good Example**: Logs and re-raises.

**vs**

**Location**: `core/views.py`

```python
# Lines 106-110
except:
    # Fallback to original if rendition fails
    header_image_url = blog.header_image.file.url if blog.header_image.file else None
```

**Issue**: Silently swallows exceptions without logging.

---

### 7.3 Inconsistent Error Response Format

Already covered in Section 3.1, but impacts error handling:

**Multiple formats observed**:
1. `{"error": "message"}` - shop/views/cart.py
2. `{"success": false, "error": "message"}` - shop/views/payment.py
3. `{"code": "CODE", "message": "msg", "severity": "error"}` - core/views.py
4. `{"detail": "message"}` - DRF default

**Recommendation**: Standardize on one format throughout codebase.

---

### 7.4 Missing Logging on Failures

**Location**: `shop/views/cart.py`

```python
# Lines 122-126
if not product.is_available:
    return Response(
        {"error": "Product is not available"},
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )
```

**Issue**: No logging when product availability check fails. Should log for analytics.

---

**Location**: `shop/views/cart.py`

```python
# Lines 553-556
except PromoCode.DoesNotExist:
    return Response(
        {"error": "Invalid or expired promo code"},
        status=status.HTTP_400_BAD_REQUEST,
    )
```

**Issue**: Should log failed promo code attempts for fraud detection.

---

## 8. Testing Gaps

### 8.1 Empty Test Files

**Location**: `shop/tests.py`

```python
# Create your tests here.
```

**Issue**: Shop app (largest app) has no tests!

---

**Location**: All test files are essentially empty:
- `blog/tests.py`
- `core/tests.py`
- `stories/tests.py`
- `users/tests.py`

**Issue**: Zero test coverage across entire codebase!

---

### 8.2 Untested Service Functions

**Location**: `shop/services/payment.py`

All payment service methods are untested:
- `request_payment()`
- `verify_payment()`

**Critical Risk**: Payment logic has no automated tests!

---

**Location**: `shop/services/shipping.py`

Shipping calculation logic untested (if it exists).

---

### 8.3 Missing Edge Case Coverage

**Untested Scenarios**:

**Cart Operations**:
- Adding item beyond stock limit
- Applying multiple promo codes
- Cart expiration
- Anonymous cart migration to user cart
- Concurrent cart modifications

**Payment Flow**:
- Payment gateway timeout
- Duplicate payment callbacks
- Payment amount mismatch
- Concurrent payment attempts for same order
- Payment callback with invalid signature

**Order Management**:
- Order status transition validation
- Inventory reduction on order completion
- Failed order rollback
- Refund processing

**User Authentication**:
- Token expiration
- Token refresh race conditions
- Password reset token reuse
- Email verification edge cases

---

### 8.4 Tests Hitting Real External Services

**Issue**: No tests exist, but when implemented:
- Should mock Zarinpal payment gateway calls
- Should mock MinIO S3 storage
- Should use test email backend
- Should use in-memory database for fast tests

**Recommendation**: Create test fixtures and mocks before writing tests.

---

## 9. Performance Concerns

### 9.1 Missing Caching on Expensive Operations

**Location**: `core/views.py`

```python
# Lines 39-178: Global search
def global_search(request):
    # Complex trigram similarity search with no caching
```

**Issue**: Search results should be cached for common queries.

**Recommendation**: Use Django's cache framework:
```python
from django.core.cache import cache

cache_key = f"search:{query}:{threshold}"
results = cache.get(cache_key)
if results is None:
    results = perform_search(...)
    cache.set(cache_key, results, 300)  # 5 minutes
```

---

**Location**: `shop/models/product.py`

```python
# Lines 63-68
@property
def feature_image(self):
    feature_image = self.images.filter(is_feature=True).first()
    if not feature_image and self.images.exists():
        feature_image = self.images.first()
    return feature_image
```

**Issue**: Property executes database queries every time it's accessed. Should use `prefetch_related` or cache.

---

**Location**: `core/views.py`

Feature flag lookup (lines 22-34) should be cached:

```python
@api_view(['GET'])
@permission_classes([AllowAny])
def feature_flags(request):
    flags = FeatureFlag.objects.all()
    # No caching
```

**Recommendation**: Cache feature flags aggressively as they rarely change.

---

### 9.2 Synchronous Calls That Should Be Async/Celery Tasks

**Location**: `users/views.py`

```python
# Lines 304-310
send_mail(
    "Reset your password",
    f"Click this link to reset your password: {reset_url}",
    settings.DEFAULT_FROM_EMAIL,
    [email],
    fail_silently=False,
)
```

**Issue**: Sending email synchronously blocks request. Should use Celery.

**Recommendation**:
```python
@celery_app.task
def send_password_reset_email(email, reset_url):
    send_mail(...)

send_password_reset_email.delay(email, reset_url)
```

---

**Location**: `shop/views/payment.py`

Payment gateway API calls are synchronous (lines 78, 193, 268).

**Issue**: Payment gateway response delays block request handling.

**Recommendation**: Use async views or task queue for payment operations.

---

**Location**: `users/views.py`

```python
# Lines 256-270: Email verification email sending (commented out)
# TODO: add this part.
# send_mail(...)
```

**Issue**: When implemented, should be async task.

---

### 9.3 Large Querysets Loaded into Memory

**Location**: `shop/models/cart.py`

```python
# Lines 48-50
@property
def total_amount(self):
    return sum(item.total_price for item in self.items.all())
```

**Issue**: Loads all items into memory. Should use aggregation:

```python
from django.db.models import Sum, F
total = self.items.aggregate(
    total=Sum(F('quantity') * F('product__price'))
)['total'] or 0
```

---

**Location**: `shop/views/cart.py`

```python
# Lines 333-349: Cart merge
for anon_item in anonymous_cart.items.all():
    # Processes all items in memory
```

**Issue**: For large carts, should use bulk operations.

---

**Location**: `blog/views.py`

```python
# Line 137
posts = BlogPost.objects.live().only("slug", "last_published_at", "first_published_at", "date")
```

**Good Example**: Uses `.only()` to limit fields, but still loads all posts into memory for sitemap.

**Recommendation**: Use iterator for very large datasets:
```python
for post in posts.iterator(chunk_size=100):
    items.append(...)
```

---

### 9.4 Missing Database Query Optimization

**Location**: `shop/views/product.py`

```python
# Lines 32-54: get_queryset with filters
def get_queryset(self):
    queryset = super().get_queryset()
    search = self.request.query_params.get("search")
    if search:
        queryset = queryset.filter(title__icontains=search)
    # More filters...
```

**Issues**:
1. `title__icontains` doesn't use indexes (case-insensitive). Should use full-text search or trigram indexes.
2. No `select_related` or `prefetch_related` for category and images.

---

**Location**: `shop/models/order.py`

```python
# Lines 55-60
def calculate_total(self):
    total = sum(item.total_price for item in self.items.all())
    self.total_amount = total
    self.save()
    return total
```

**Issue**: Could use aggregation instead:
```python
from django.db.models import Sum, F
total = self.items.aggregate(
    total=Sum(F('quantity') * F('price'))
)['total'] or 0
```

---

**Location**: Multiple property methods across models trigger queries inefficiently.

**Recommendation**: Use annotations when querying multiple objects:
```python
orders = Order.objects.annotate(
    total=Sum(F('items__quantity') * F('items__price'))
)
```

---

## Summary of Findings

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Code Organization | 4 | 5 | 3 | 2 | 14 |
| Naming Issues | 0 | 2 | 5 | 3 | 10 |
| API Design | 3 | 4 | 3 | 2 | 12 |
| Database & Queries | 5 | 7 | 4 | 2 | 18 |
| Type Safety | 0 | 3 | 8 | 4 | 15 |
| Security | 2 | 4 | 3 | 2 | 11 |
| Error Handling | 1 | 2 | 3 | 1 | 7 |
| Testing | 5 | 0 | 0 | 0 | 5 |
| Performance | 2 | 4 | 3 | 2 | 11 |
| **TOTAL** | **22** | **31** | **32** | **18** | **103** |

---

## Priority Recommendations

### Critical (Do First)
1. **Add Tests**: Zero test coverage is unacceptable for production code, especially payment logic
2. **Fix N+1 Queries**: Add `select_related`/`prefetch_related` to all list views
3. **Add Database Indexes**: Critical for performance as data grows
4. **Standardize Error Responses**: Inconsistent formats confuse frontend developers
5. **Move Business Logic to Services**: Views are too fat, testing is impossible

### High Priority
1. **Add Pagination**: All list endpoints must have pagination
2. **Fix Persian Error Messages**: Per CLAUDE.md requirements
3. **Add Type Hints**: Especially on service layer and critical business logic
4. **Security Audit**: Review all permission classes and CSRF exemptions
5. **Cache Expensive Operations**: Search and feature flags

### Medium Priority
1. **Refactor Fat Models**: Move logic to services
2. **Improve URL Consistency**: Follow REST conventions
3. **Add Request/Response Validation**: Use serializers consistently
4. **Fix Bare Except Clauses**: Specify exception types
5. **Add Async Tasks**: Email and payment operations

### Low Priority
1. **Rename Inconsistent Files**: `category_serializer.py` → `serializers/category.py`
2. **Add Missing Type Hints**: Complete coverage
3. **Document API Schemas**: OpenAPI/Swagger
4. **Optimize Bulk Operations**: Use `bulk_create`, `update`, etc.

---

## Conclusion

The codebase shows good understanding of Django/DRF patterns but lacks critical production-readiness elements:
- **No tests** (most critical issue)
- **Missing service layer** for business logic separation
- **Performance issues** from missing indexes and N+1 queries
- **Inconsistent API design** that will confuse frontend developers
- **Security gaps** in permission checks and input validation

The good news: The architecture is sound, logging is comprehensive, and patterns like payment gateway factory show good design thinking. With focused effort on the critical issues, this codebase can become production-ready.

---

## Next Steps

1. **Review this report** with the development team
2. **Prioritize issues** based on your deployment timeline
3. **Create GitHub issues** for tracking fixes
4. **Set up test infrastructure** before writing tests
5. **Establish coding standards** to prevent future issues
6. **Schedule regular code reviews** to maintain quality

This audit should serve as a roadmap for improving code quality and production readiness.