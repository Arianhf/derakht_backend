# Refactoring Plan - Sequential PR Checklist

**Total PRs**: 35
**Estimated Timeline**: 6-8 weeks (assuming 1-2 PRs per day)

---

## Phase 1: Security Fixes (PRs 1-6)

### ✅ PR #1: Fix Bare Except Clauses
**Risk Level**: Low
**Estimated Lines**: ~50 lines
**Dependencies**: None

**Scope**: Replace bare `except:` with `except Exception:` and add proper logging

**Files to Modify**:
- `core/views.py` (lines 106-110, 134-140)
- Any other files with bare excepts found in codebase

**Changes**:
```python
# Before
try:
    rendition = blog.header_image.get_rendition('fill-400x300')
    header_image_url = rendition.url
except:
    header_image_url = ...

# After
try:
    rendition = blog.header_image.get_rendition('fill-400x300')
    header_image_url = rendition.url
except Exception as e:
    logger.warning(f"Failed to generate rendition: {e}")
    header_image_url = ...
```

**Verification**:
```bash
# Search for remaining bare excepts
grep -r "except:" --include="*.py" . | grep -v "# except:"

# Run existing functionality
python manage.py runserver
# Test blog post rendering, product images
```

---

### ✅ PR #2: Add Explicit AllowAny Permission Classes
**Risk Level**: Low
**Estimated Lines**: ~30 lines
**Dependencies**: None

**Scope**: Replace empty `permission_classes = []` with explicit `[AllowAny]`

**Files to Modify**:
- `blog/views.py` (line 20)
- `shop/views/product.py` (line 155)
- `shop/views/payment.py` (line 168 - add comment explaining why)

**Changes**:
```python
# Before
permission_classes = []

# After
from rest_framework.permissions import AllowAny

permission_classes = [AllowAny]  # Public endpoint for blog content
```

**Verification**:
```bash
# Search for empty permission classes
grep -r "permission_classes = \[\]" --include="*.py" .

# Test unauthenticated API access
curl http://localhost:8000/api/blog/posts/
curl http://localhost:8000/api/shop/products/
```

---

### ✅ PR #3: Sanitize Sensitive Data from Logs
**Risk Level**: Low
**Estimated Lines**: ~80 lines
**Dependencies**: None

**Scope**: Remove or hash sensitive data before logging

**Files to Modify**:
- `shop/views/payment.py` (lines 185-188)
- `users/views.py` (lines 158-159)
- `core/logging_utils.py` (add sanitization helpers)

**Changes**:
```python
# Add to core/logging_utils.py
def sanitize_payment_params(params: dict) -> dict:
    """Remove sensitive payment data from logs"""
    safe_params = params.copy()
    sensitive_keys = ['card_number', 'cvv', 'password', 'token']
    for key in sensitive_keys:
        if key in safe_params:
            safe_params[key] = '***REDACTED***'
    return safe_params

def hash_email(email: str) -> str:
    """Hash email for privacy-preserving logs"""
    import hashlib
    return hashlib.sha256(email.encode()).hexdigest()[:16]

# In payment.py
extra={
    "extra_data": {
        "callback_params": sanitize_payment_params(request.GET.dict()),
    }
}

# In users/views.py
extra={
    "email_hash": hash_email(email),
    "ip_address": get_client_ip(request),
}
```

**Verification**:
```bash
# Check logs after triggering payment callback
tail -f logs/derakht.log | grep -i "callback_params"

# Check logs after password reset
tail -f logs/security.log | grep -i "email"

# Ensure no plain emails or sensitive data appear
```

---

### ✅ PR #4: Add Cart Input Validation Serializers
**Risk Level**: Medium
**Estimated Lines**: ~120 lines
**Dependencies**: None

**Scope**: Replace manual validation with proper serializers in cart views

**Files to Modify**:
- `shop/serializers/cart.py` (add new serializers)
- `shop/views/cart.py` (lines 162-187, 240-260)

**Changes**:
```python
# In shop/serializers/cart.py
class AddCartItemSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    anonymous_cart_id = serializers.UUIDField(required=False, allow_null=True)

class UpdateCartItemSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=0)
    anonymous_cart_id = serializers.UUIDField(required=False, allow_null=True)

class RemoveCartItemSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    anonymous_cart_id = serializers.UUIDField(required=False, allow_null=True)

# In shop/views/cart.py
def add_item(self, request):
    serializer = AddCartItemSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    product_id = data['product_id']
    quantity = data['quantity']
    anonymous_cart_id = data.get('anonymous_cart_id')
    # ... rest of logic
```

**Verification**:
```bash
# Run tests
python manage.py test shop.tests

# Manual API tests
curl -X POST http://localhost:8000/api/shop/cart/add_item/ \
  -H "Content-Type: application/json" \
  -d '{"product_id": "invalid", "quantity": -1}'
# Should return 400 with validation errors

curl -X POST http://localhost:8000/api/shop/cart/add_item/ \
  -H "Content-Type: application/json" \
  -d '{"product_id": "valid-uuid", "quantity": 2}'
# Should work
```

---

### ✅ PR #5: Add Payment Input Validation Serializers
**Risk Level**: Medium
**Estimated Lines**: ~100 lines
**Dependencies**: None

**Scope**: Add serializers for payment verification endpoints

**Files to Modify**:
- `shop/serializers/payment.py` (create new file)
- `shop/views/payment.py` (lines 371-378, other validation points)

**Changes**:
```python
# Create shop/serializers/payment.py
from rest_framework import serializers

class PaymentVerificationSerializer(serializers.Serializer):
    order_id = serializers.UUIDField(required=True)
    transaction_id = serializers.CharField(required=True, max_length=100)
    authority = serializers.CharField(required=False, max_length=100)

class ManualPaymentSerializer(serializers.Serializer):
    order_id = serializers.UUIDField(required=True)
    transaction_id = serializers.CharField(required=True, max_length=100)
    amount = serializers.DecimalField(max_digits=10, decimal_places=0)
    reference_id = serializers.CharField(max_length=100, required=False)

# In shop/views/payment.py
from shop.serializers.payment import PaymentVerificationSerializer

def verify_manual_payment(self, request):
    serializer = PaymentVerificationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    # ... use serializer.validated_data
```

**Verification**:
```bash
# Test invalid requests
curl -X POST http://localhost:8000/api/shop/payments/verify/ \
  -H "Content-Type: application/json" \
  -d '{}'
# Should return 400 with validation errors

# Test valid request
curl -X POST http://localhost:8000/api/shop/payments/verify/ \
  -H "Content-Type: application/json" \
  -d '{"order_id": "valid-uuid", "transaction_id": "12345"}'
```

---

### ✅ PR #6: Document CSRF Exemptions with Security Notes
**Risk Level**: Low
**Estimated Lines**: ~60 lines
**Dependencies**: None

**Scope**: Add detailed comments explaining why CSRF is exempt and what security measures exist

**Files to Modify**:
- `shop/views/payment.py` (line 163)
- `users/views.py` (line 248)
- `stories/views.py` (lines 399, 459, 485, 588, 718, 777)
- Create `SECURITY.md` documenting all exemptions

**Changes**:
```python
# In shop/views/payment.py
@method_decorator(csrf_exempt, name="dispatch")
class PaymentCallbackView(APIView):
    """
    CSRF exempt because:
    1. This is a callback from external payment gateway (Zarinpal)
    2. Request originates from Zarinpal's servers, not user's browser
    3. Security is ensured by:
       - Verifying payment with gateway using authority token
       - Checking order status to prevent duplicate processing
       - Validating payment amount matches order total

    TODO: Add gateway signature verification for additional security
    """
    permission_classes = [AllowAny]
```

**Verification**:
```bash
# Review all CSRF exemptions
grep -r "@method_decorator(csrf_exempt" --include="*.py" .

# Check SECURITY.md is created
cat SECURITY.md
```

---

## Phase 2: Bug-Prone Patterns (PRs 7-8)

### ✅ PR #7: Add Missing Error Logging
**Risk Level**: Low
**Estimated Lines**: ~80 lines
**Dependencies**: None

**Scope**: Add logging for business validation failures and exceptions

**Files to Modify**:
- `shop/views/cart.py` (lines 122-126, 553-556)
- `shop/views/payment.py` (add logging to validation failures)
- `stories/views.py` (add logging to upload failures)

**Changes**:
```python
# In shop/views/cart.py
from core.logging_utils import get_logger

logger = get_logger(__name__)

# Line 122-126
if not product.is_available:
    logger.warning(
        "Attempt to add unavailable product to cart",
        extra={"extra_data": {
            "product_id": str(product.id),
            "user_id": str(request.user.id) if request.user.is_authenticated else None,
        }}
    )
    return Response(...)

# Line 553-556
except PromoCode.DoesNotExist:
    logger.warning(
        "Invalid promo code attempt",
        extra={"extra_data": {
            "code": code,
            "cart_id": str(cart.id),
        }}
    )
    return Response(...)
```

**Verification**:
```bash
# Trigger validation failures and check logs
tail -f logs/derakht.log

# Try to add unavailable product
curl -X POST .../cart/add_item/ -d '{"product_id": "unavailable-product-id"}'

# Try invalid promo code
curl -X POST .../cart/apply_promo/ -d '{"code": "INVALID"}'

# Verify log entries appear
```

---

### ✅ PR #8: Improve Exception Handling Consistency
**Risk Level**: Low
**Estimated Lines**: ~70 lines
**Dependencies**: None

**Scope**: Ensure all try-except blocks log before returning errors

**Files to Modify**:
- `shop/views/cart.py` (various exception handlers)
- `shop/views/payment.py` (ensure all exceptions logged)
- `core/views.py` (add logging to swallowed exceptions)

**Changes**:
```python
# Pattern to apply everywhere
try:
    # ... operation
except SpecificException as e:
    logger.error(
        "Operation failed",
        extra={"extra_data": {"error": str(e), "context": "..."}}
    )
    return Response({"error": "User-friendly message"}, status=400)
```

**Verification**:
```bash
# Check all exception handlers have logging
grep -A 5 "except.*:" --include="*.py" shop/views/*.py | grep -B 5 "logger"

# Trigger exceptions and verify logs
tail -f logs/errors.log
```

---

## Phase 3: Performance - Database (PRs 9-15)

### ✅ PR #9: Add Database Indexes (Migration Only)
**Risk Level**: Low
**Estimated Lines**: ~150 lines (migration file)
**Dependencies**: None

**Scope**: Create migration adding indexes to frequently queried fields

**Files to Modify**:
- `shop/models/product.py`
- `shop/models/order.py`
- `shop/models/payment.py`
- `stories/models.py`

**Changes**:
```python
# In shop/models/product.py
class Product(BaseModel):
    # ... existing fields

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        indexes = [
            models.Index(fields=['is_active', 'is_available', 'is_visible'], name='product_active_idx'),
            models.Index(fields=['category', '-created_at'], name='product_category_idx'),
            models.Index(fields=['min_age', 'max_age'], name='product_age_idx'),
            models.Index(fields=['slug'], name='product_slug_idx'),
        ]

# In shop/models/order.py
class Order(BaseModel):
    # ... existing fields

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status', '-created_at'], name='order_user_status_idx'),
            models.Index(fields=['status', '-created_at'], name='order_status_idx'),
        ]

# In shop/models/payment.py
class Payment(BaseModel):
    # ... existing fields

    class Meta:
        indexes = [
            models.Index(fields=['order'], name='payment_order_idx'),
            models.Index(fields=['status', '-created_at'], name='payment_status_idx'),
        ]

# In stories/models.py
class Story(models.Model):
    # ... existing fields

    class Meta:
        indexes = [
            models.Index(fields=['author', 'status'], name='story_author_status_idx'),
            models.Index(fields=['status', '-created_date'], name='story_status_date_idx'),
        ]
```

**Verification**:
```bash
# Create migrations
python manage.py makemigrations

# Review migration file
cat shop/migrations/000X_add_indexes.py

# Apply in development
python manage.py migrate

# Check indexes created
python manage.py dbshell
\d shop_product
\d shop_order
\d shop_payment
\d stories_story
# Should see new indexes

# DON'T apply to production yet - wait for performance testing
```

---

### ✅ PR #10: Add Pagination to All List Endpoints
**Risk Level**: Low
**Estimated Lines**: ~100 lines
**Dependencies**: None

**Scope**: Add pagination configuration to all ViewSets

**Files to Modify**:
- `derakht/settings.py` (add pagination config)
- `shop/views/product.py`
- `shop/views/order.py`
- `users/views.py` (AddressViewSet)
- `stories/views.py`

**Changes**:
```python
# In derakht/settings.py
REST_FRAMEWORK = {
    # ... existing config
    'PAGE_SIZE': 20,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
}

# In shop/views/product.py
from rest_framework.pagination import PageNumberPagination

class ProductPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = ProductPagination
    # ... rest of viewset

# In shop/views/order.py
class OrderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = OrderPagination
    # ... rest of viewset

# Similar for AddressViewSet, StoryViewSet
```

**Verification**:
```bash
# Test pagination
curl "http://localhost:8000/api/shop/products/?page=1"
# Should return paginated response with count, next, previous, results

curl "http://localhost:8000/api/shop/products/?page=1&page_size=10"
# Should return 10 items

curl "http://localhost:8000/api/shop/orders/?page=1"
# Should return paginated orders

# Verify response format
{
    "count": 100,
    "next": "http://.../products/?page=2",
    "previous": null,
    "results": [...]
}
```

---

### ✅ PR #11: Fix N+1 Queries in Shop Product Views
**Risk Level**: Medium
**Estimated Lines**: ~80 lines
**Dependencies**: None

**Scope**: Add select_related/prefetch_related to product querysets

**Files to Modify**:
- `shop/views/product.py`
- `shop/serializers/product.py` (verify it uses prefetched data)

**Changes**:
```python
# In shop/views/product.py
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        queryset = Product.objects.filter(
            is_active=True,
            is_available=True,
            is_visible=True
        ).select_related(
            'category'
        ).prefetch_related(
            'images',
            'tags',
        )

        # ... filters
        return queryset

# In shop/serializers/product.py - verify it doesn't trigger additional queries
class ProductListSerializer(serializers.ModelSerializer):
    # Use prefetched data, don't add new queries
    feature_image = serializers.SerializerMethodField()

    def get_feature_image(self, obj):
        # This should use prefetched images
        images = list(obj.images.all())  # Already prefetched
        feature = next((img for img in images if img.is_feature), None)
        if not feature and images:
            feature = images[0]
        return ImageSerializer(feature).data if feature else None
```

**Verification**:
```bash
# Install django-debug-toolbar or use logging
# Add to settings.py temporarily
LOGGING['loggers']['django.db.backends'] = {
    'level': 'DEBUG',
    'handlers': ['console'],
}

# Test endpoint
curl http://localhost:8000/api/shop/products/

# Check query count in logs
# Should see:
# - 1 query for products
# - 1 query for categories (select_related)
# - 1 query for images (prefetch_related)
# - 1 query for tags (prefetch_related)
# Total: ~4 queries instead of N+1

# Or use Django Debug Toolbar in browser
# Navigate to /api/shop/products/
# Check SQL panel - should show minimal queries
```

---

### ✅ PR #12: Fix N+1 Queries in Shop Cart Views
**Risk Level**: Medium
**Estimated Lines**: ~60 lines
**Dependencies**: None

**Scope**: Add prefetch to cart item queries

**Files to Modify**:
- `shop/views/cart.py`
- `shop/serializers/cart.py`

**Changes**:
```python
# In shop/views/cart.py
def get_cart(self, request, anonymous_cart_id=None):
    # ... existing logic to get cart

    # Add prefetch when accessing items
    cart.items.all()  # OLD

    cart = Cart.objects.prefetch_related(
        'items__product__images',
        'items__product__category',
    ).get(id=cart.id)  # NEW

    # Or at the query level:
    data = {
        "id": cart.id,
        "items": cart.items.select_related('product').prefetch_related(
            'product__images',
            'product__category'
        ).all(),
        # ...
    }
```

**Verification**:
```bash
# Enable query logging
# Test cart retrieval
curl http://localhost:8000/api/shop/cart/

# Should see:
# - 1 query for cart
# - 1 query for cart items + products (select_related)
# - 1 query for product images (prefetch_related)
# - 1 query for categories (prefetch_related)
# Total: ~4 queries regardless of cart size
```

---

### ✅ PR #13: Fix N+1 Queries in Shop Order Views
**Risk Level**: Medium
**Estimated Lines**: ~50 lines
**Dependencies**: None

**Scope**: Optimize order queryset prefetching

**Files to Modify**:
- `shop/views/order.py`

**Changes**:
```python
# In shop/views/order.py
class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        return Order.objects.filter(
            user=self.request.user
        ).select_related(
            'shipping_info',
            'promo_code',
        ).prefetch_related(
            'items__product__images',
            'items__product__category',
            'payments',
        ).order_by('-created_at')
```

**Verification**:
```bash
# Test order list
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/shop/orders/

# Check query count - should be consistent regardless of number of orders
```

---

### ✅ PR #14: Fix N+1 Queries in Blog Views
**Risk Level**: Low
**Estimated Lines**: ~70 lines
**Dependencies**: None

**Scope**: Add prefetch to blog post queries

**Files to Modify**:
- `blog/views.py`

**Changes**:
```python
# In blog/views.py
# Line 318-324
category_posts = (
    BlogPost.objects.live()
    .filter(categories__in=post.categories.all())
    .exclude(id__in=included_ids)
    .select_related('header_image')
    .prefetch_related('categories', 'tags', 'authors')
    .distinct()
    .order_by("-date")[:needed]
)

# Similar optimizations for other blog queries
```

**Verification**:
```bash
# Test blog post detail with related posts
curl http://localhost:8000/api/blog/posts/<slug>/

# Check query count
```

---

### ✅ PR #15: Fix N+1 Queries in Stories Views
**Risk Level**: Medium
**Estimated Lines**: ~60 lines
**Dependencies**: None

**Scope**: Optimize story part queries

**Files to Modify**:
- `stories/views.py`

**Changes**:
```python
# In stories/views.py
class StoryViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        queryset = Story.objects.filter(
            author=self.request.user
        ).select_related(
            'template',
            'author',
        ).prefetch_related(
            'parts__template_part',
        )
        return queryset

# When creating story from template (line 109-122)
template_parts = template.template_parts.select_related(
    'template'
).all()
```

**Verification**:
```bash
# Test story list
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/stories/

# Test story creation from template
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/stories/create_from_template/ \
  -d '{"template_id": "uuid"}'

# Check query count
```

---

### ✅ PR #16: Use bulk_create for Cart Checkout
**Risk Level**: Medium
**Estimated Lines**: ~40 lines
**Dependencies**: None

**Scope**: Replace loop with bulk_create for order items

**Files to Modify**:
- `shop/views/cart.py` (lines 504-510)

**Changes**:
```python
# In shop/views/cart.py - checkout method
# OLD (lines 504-510)
for cart_item in cart.items.all():
    OrderItem.objects.create(
        order=order,
        product=cart_item.product,
        quantity=cart_item.quantity,
        price=cart_item.product.price,
    )

# NEW
cart_items = cart.items.select_related('product').all()
order_items = [
    OrderItem(
        order=order,
        product=item.product,
        quantity=item.quantity,
        price=item.product.price,
    )
    for item in cart_items
]
OrderItem.objects.bulk_create(order_items)
```

**Verification**:
```bash
# Test checkout flow
# 1. Add items to cart
# 2. Checkout
# 3. Verify order items created correctly
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/shop/cart/checkout/ \
  -d '{"shipping_address_id": "uuid"}'

# Check order items exist
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/shop/orders/<order_id>/

# Verify performance improvement with query logging
```

---

### ✅ PR #17: Use bulk_create for Story Creation
**Risk Level**: Medium
**Estimated Lines**: ~50 lines
**Dependencies**: None

**Scope**: Replace loop with bulk_create for story parts

**Files to Modify**:
- `stories/views.py` (lines 109-122)

**Changes**:
```python
# In stories/views.py - create_from_template
# OLD
for story_part_template in template.template_parts.all():
    canvas_text_data = copy.deepcopy(...)
    canvas_illustration_data = copy.deepcopy(...)
    StoryPart.objects.create(...)
    parts_created += 1

# NEW
template_parts = template.template_parts.all()
story_parts = []
for story_part_template in template_parts:
    canvas_text_data = copy.deepcopy(
        story_part_template.canvas_text_template or []
    )
    canvas_illustration_data = copy.deepcopy(
        story_part_template.canvas_illustration_template or []
    )
    story_parts.append(
        StoryPart(
            story=story,
            template_part=story_part_template,
            order=story_part_template.order,
            canvas_text_data=canvas_text_data,
            canvas_illustration_data=canvas_illustration_data,
        )
    )

StoryPart.objects.bulk_create(story_parts)
parts_created = len(story_parts)
```

**Verification**:
```bash
# Test story creation from template
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/stories/create_from_template/ \
  -d '{"template_id": "uuid"}'

# Verify all parts created
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/stories/<story_id>/

# Check query count - should use bulk_create instead of N creates
```

---

### ✅ PR #18: Add Caching to Feature Flags
**Risk Level**: Low
**Estimated Lines**: ~40 lines
**Dependencies**: None

**Scope**: Cache feature flags for 5 minutes

**Files to Modify**:
- `core/views.py` (lines 22-34)
- `derakht/settings.py` (ensure cache configured)

**Changes**:
```python
# In derakht/settings.py - verify cache is configured
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'db': 1,
        },
        'KEY_PREFIX': 'derakht',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# In core/views.py
from django.core.cache import cache

@api_view(['GET'])
@permission_classes([AllowAny])
def feature_flags(request):
    cache_key = 'feature_flags:all'
    flags_data = cache.get(cache_key)

    if flags_data is None:
        flags = FeatureFlag.objects.filter(is_active=True)
        serializer = FeatureFlagSerializer(flags, many=True)
        flags_data = serializer.data
        cache.set(cache_key, flags_data, 300)  # Cache for 5 minutes

    return Response(flags_data)
```

**Verification**:
```bash
# Test feature flags endpoint
curl http://localhost:8000/api/core/feature-flags/

# Check Redis cache
redis-cli
> KEYS derakht:feature_flags:*
> GET derakht:feature_flags:all

# Test cache invalidation - update a flag in admin
# Wait 5 minutes or flush cache
> DEL derakht:feature_flags:all
# Request again, should rebuild cache
```

---

### ✅ PR #19: Add Caching to Search Results
**Risk Level**: Medium
**Estimated Lines**: ~80 lines
**Dependencies**: None

**Scope**: Cache search results for common queries

**Files to Modify**:
- `core/views.py` (lines 39-178)

**Changes**:
```python
# In core/views.py
from django.core.cache import cache
import hashlib

@api_view(['GET'])
@permission_classes([AllowAny])
def global_search(request):
    query = request.GET.get('q', '').strip()
    threshold = float(request.GET.get('threshold', 0.1))

    if not query:
        return Response({"results": []})

    # Create cache key from query and threshold
    cache_key = f"search:{hashlib.md5(f'{query}:{threshold}'.encode()).hexdigest()}"
    cached_results = cache.get(cache_key)

    if cached_results is not None:
        return Response(cached_results)

    # Perform search (existing logic)
    blog_results = []
    product_results = []
    # ... existing search logic

    results = {
        "blog": blog_results,
        "products": product_results,
    }

    # Cache for 5 minutes
    cache.set(cache_key, results, 300)

    return Response(results)
```

**Verification**:
```bash
# Test search
curl "http://localhost:8000/api/core/search/?q=test"

# Check cache
redis-cli
> KEYS derakht:search:*

# Run same search again - should be faster
time curl "http://localhost:8000/api/core/search/?q=test"
```

---

## Phase 4: Code Organization (PRs 20-26)

### ✅ PR #20: Create Cart Service Layer
**Risk Level**: Medium
**Estimated Lines**: ~250 lines
**Dependencies**: None

**Scope**: Extract cart business logic from views to service

**Files to Modify**:
- `shop/services/cart.py` (create new file)
- `shop/views/cart.py` (refactor to use service)

**Changes**:
```python
# Create shop/services/cart.py
from typing import Tuple, Optional
from decimal import Decimal
from django.contrib.auth.models import User
from shop.models import Cart, Product, CartItem, PromoCode
from core.logging_utils import get_logger

logger = get_logger(__name__)

class CartService:
    """Business logic for cart operations"""

    @staticmethod
    def get_or_create_cart(
        user: Optional[User] = None,
        anonymous_id: Optional[str] = None
    ) -> Tuple[Cart, bool]:
        """Get or create cart for user or anonymous session"""
        if user and user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=user, status='ACTIVE')
        elif anonymous_id:
            cart, created = Cart.objects.get_or_create(
                anonymous_id=anonymous_id,
                status='ACTIVE'
            )
        else:
            raise ValueError("Either user or anonymous_id required")
        return cart, created

    @staticmethod
    def add_item(cart: Cart, product: Product, quantity: int) -> CartItem:
        """Add or update product in cart"""
        if not product.is_available:
            raise ValueError("Product is not available")

        if quantity < 1:
            raise ValueError("Quantity must be positive")

        # Check stock if applicable
        if hasattr(product, 'stock') and product.stock < quantity:
            raise ValueError(f"Only {product.stock} items available")

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        logger.info(
            "Item added to cart",
            extra={"extra_data": {
                "cart_id": str(cart.id),
                "product_id": str(product.id),
                "quantity": quantity,
            }}
        )

        return cart_item

    @staticmethod
    def update_quantity(cart: Cart, product: Product, quantity: int) -> CartItem:
        """Update item quantity in cart"""
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")

        cart_item = CartItem.objects.get(cart=cart, product=product)

        if quantity == 0:
            cart_item.delete()
            return None

        cart_item.quantity = quantity
        cart_item.save()
        return cart_item

    @staticmethod
    def apply_promo_code(cart: Cart, code: str) -> Tuple[PromoCode, Decimal]:
        """Apply promo code and return discount amount"""
        try:
            promo = PromoCode.objects.get(
                code=code,
                is_active=True,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now()
            )
        except PromoCode.DoesNotExist:
            logger.warning(f"Invalid promo code attempt: {code}")
            raise ValueError("Invalid or expired promo code")

        # Validate usage limits
        if promo.max_uses and promo.used_count >= promo.max_uses:
            raise ValueError("Promo code usage limit reached")

        # Calculate cart total
        total_amount = sum(item.total_price for item in cart.items.all())

        # Validate minimum purchase
        if total_amount < promo.min_purchase:
            raise ValueError(
                f"Minimum purchase of {promo.min_purchase} required"
            )

        # Calculate discount
        if promo.discount_type == "fixed":
            discount_amount = promo.discount_value
        else:  # percentage
            discount_amount = total_amount * (promo.discount_value / 100)

        # Apply to cart
        cart.promo_code = promo
        cart.discount_amount = discount_amount
        cart.save()

        logger.info(
            "Promo code applied",
            extra={"extra_data": {
                "cart_id": str(cart.id),
                "promo_code": code,
                "discount": float(discount_amount),
            }}
        )

        return promo, discount_amount

# In shop/views/cart.py - refactor to use service
from shop.services.cart import CartService

class CartViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["post"])
    def add_item(self, request):
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            cart, _ = CartService.get_or_create_cart(
                user=request.user if request.user.is_authenticated else None,
                anonymous_id=data.get('anonymous_cart_id')
            )

            product = Product.objects.get(id=data['product_id'])
            cart_item = CartService.add_item(cart, product, data['quantity'])

            return Response(
                CartItemSerializer(cart_item).data,
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
```

**Verification**:
```bash
# Run all cart-related tests
python manage.py test shop.tests.CartTestCase

# Manual tests
curl -X POST .../cart/add_item/ -d '{"product_id": "...", "quantity": 2}'
curl -X POST .../cart/update_quantity/ -d '{"product_id": "...", "quantity": 5}'
curl -X POST .../cart/apply_promo/ -d '{"code": "SUMMER10"}'

# Verify logs
tail -f logs/derakht.log | grep "cart"
```

---

### ✅ PR #21: Create Order Service Layer
**Risk Level**: Medium
**Estimated Lines**: ~200 lines
**Dependencies**: PR #20 (CartService)

**Scope**: Extract order creation and management logic to service

**Files to Modify**:
- `shop/services/order.py` (create new file)
- `shop/views/cart.py` (refactor checkout to use OrderService)

**Changes**:
```python
# Create shop/services/order.py
from typing import Dict, Any
from decimal import Decimal
from django.db import transaction
from django.contrib.auth.models import User
from shop.models import Cart, Order, OrderItem, ShippingInfo, Address
from core.logging_utils import get_logger

logger = get_logger(__name__)

class OrderService:
    """Business logic for order operations"""

    @staticmethod
    @transaction.atomic
    def create_from_cart(
        cart: Cart,
        shipping_address: Address,
        user: User,
        shipping_cost: Decimal = Decimal('0'),
        notes: str = ''
    ) -> Order:
        """Create order from cart"""
        # Validate cart not empty
        cart_items = cart.items.select_related('product').all()
        if not cart_items:
            raise ValueError("Cart is empty")

        # Calculate total
        subtotal = sum(item.total_price for item in cart_items)
        discount = cart.discount_amount or Decimal('0')
        total = subtotal - discount + shipping_cost

        # Create order
        order = Order.objects.create(
            user=user,
            status='PENDING',
            subtotal_amount=subtotal,
            discount_amount=discount,
            shipping_cost=shipping_cost,
            total_amount=total,
            promo_code=cart.promo_code,
            notes=notes,
        )

        # Create shipping info
        ShippingInfo.objects.create(
            order=order,
            recipient_name=shipping_address.recipient_name,
            phone_number=shipping_address.phone_number,
            address_line1=shipping_address.address_line1,
            address_line2=shipping_address.address_line2,
            city=shipping_address.city,
            state=shipping_address.state,
            postal_code=shipping_address.postal_code,
        )

        # Create order items (bulk)
        order_items = [
            OrderItem(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
            )
            for item in cart_items
        ]
        OrderItem.objects.bulk_create(order_items)

        # Clear cart
        cart.items.all().delete()
        cart.status = 'COMPLETED'
        cart.save()

        # Update promo code usage
        if cart.promo_code:
            cart.promo_code.used_count += 1
            cart.promo_code.save()

        logger.info(
            "Order created from cart",
            extra={"extra_data": {
                "order_id": str(order.id),
                "cart_id": str(cart.id),
                "total": float(total),
            }}
        )

        return order

    @staticmethod
    def calculate_total(order: Order) -> Decimal:
        """Recalculate order total"""
        from django.db.models import Sum, F

        subtotal = order.items.aggregate(
            total=Sum(F('quantity') * F('price'))
        )['total'] or Decimal('0')

        total = subtotal - order.discount_amount + order.shipping_cost
        return total

# In shop/views/cart.py
from shop.services.order import OrderService

@action(detail=False, methods=["post"])
def checkout(self, request):
    # ... validation

    try:
        order = OrderService.create_from_cart(
            cart=cart,
            shipping_address=shipping_address,
            user=request.user,
            shipping_cost=shipping_cost,
            notes=notes
        )

        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED
        )
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
```

**Verification**:
```bash
# Test checkout flow
curl -X POST -H "Authorization: Bearer <token>" \
  .../cart/checkout/ \
  -d '{"shipping_address_id": "uuid", "notes": "test"}'

# Verify order created
curl -H "Authorization: Bearer <token>" \
  .../orders/

# Verify cart cleared
curl -H "Authorization: Bearer <token>" \
  .../cart/

# Check logs
tail -f logs/derakht.log | grep "Order created"
```

---

### ✅ PR #22: Create Auth Service Layer
**Risk Level**: Medium
**Estimated Lines**: ~180 lines
**Dependencies**: None

**Scope**: Extract authentication logic from users views

**Files to Modify**:
- `users/services/auth.py` (create new file)
- `users/views.py` (refactor password reset to use service)

**Changes**:
```python
# Create users/services/auth.py
from typing import Dict, Tuple
from datetime import datetime, timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
import jwt
from core.logging_utils import get_logger

logger = get_logger(__name__)
User = get_user_model()

class AuthService:
    """Business logic for authentication operations"""

    @staticmethod
    def generate_reset_token(user: User, expiry_hours: int = 24) -> str:
        """Generate password reset token"""
        token = jwt.encode(
            {
                "user_id": str(user.id),
                "exp": datetime.utcnow() + timedelta(hours=expiry_hours),
                "type": "password_reset"
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )

        logger.info(
            "Password reset token generated",
            extra={"extra_data": {
                "user_id": str(user.id),
                "expiry_hours": expiry_hours,
            }}
        )

        return token

    @staticmethod
    def verify_reset_token(token: str) -> User:
        """Verify password reset token and return user"""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )

            if payload.get("type") != "password_reset":
                raise ValueError("Invalid token type")

            user = User.objects.get(id=payload["user_id"])
            return user

        except jwt.ExpiredSignatureError:
            logger.warning("Expired reset token used")
            raise ValueError("Reset link has expired")
        except jwt.InvalidTokenError:
            logger.warning("Invalid reset token used")
            raise ValueError("Invalid reset link")
        except User.DoesNotExist:
            logger.warning(f"Reset token for non-existent user: {payload.get('user_id')}")
            raise ValueError("Invalid reset link")

    @staticmethod
    def send_reset_email(user: User, reset_url: str) -> None:
        """Send password reset email (sync version)"""
        # TODO: Convert to async task in separate PR
        subject = "بازنشانی رمز عبور"
        message = f"""
        سلام {user.first_name or user.email},

        برای بازنشانی رمز عبور خود روی لینک زیر کلیک کنید:
        {reset_url}

        این لینک تا ۲۴ ساعت معتبر است.

        اگر شما این درخواست را ننموده‌اید، این ایمیل را نادیده بگیرید.

        با تشکر،
        تیم درخت
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        logger.info(
            "Password reset email sent",
            extra={"extra_data": {
                "user_id": str(user.id),
            }}
        )

# In users/views.py
from users.services.auth import AuthService

class RequestPasswordResetView(APIView):
    def post(self, request):
        email = request.data.get("email")

        try:
            user = User.objects.get(email=email)
            token = AuthService.generate_reset_token(user)
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
            AuthService.send_reset_email(user, reset_url)

            return Response(
                {"message": "ایمیل بازنشانی رمز عبور ارسال شد"},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            # Don't reveal if email exists
            return Response(
                {"message": "ایمیل بازنشانی رمز عبور ارسال شد"},
                status=status.HTTP_200_OK
            )

class ResetPasswordView(APIView):
    def post(self, request):
        token = request.data.get("token")
        new_password = request.data.get("password")

        try:
            user = AuthService.verify_reset_token(token)
            user.set_password(new_password)
            user.save()

            return Response(
                {"message": "رمز عبور با موفقیت تغییر کرد"},
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
```

**Verification**:
```bash
# Test password reset flow
curl -X POST .../users/request-password-reset/ \
  -d '{"email": "user@example.com"}'

# Check email sent (check logs or test email backend)
tail -f logs/security.log | grep "Password reset"

# Test reset with token
curl -X POST .../users/reset-password/ \
  -d '{"token": "...", "password": "newpass123"}'

# Test login with new password
curl -X POST .../users/login/ \
  -d '{"email": "user@example.com", "password": "newpass123"}'
```

---

### ✅ PR #23: Create Search Service Layer
**Risk Level**: Medium
**Estimated Lines**: ~220 lines
**Dependencies**: PR #19 (caching)

**Scope**: Extract search logic from core views

**Files to Modify**:
- `core/services/search.py` (create new file)
- `core/views.py` (refactor to use SearchService)

**Changes**:
```python
# Create core/services/search.py
from typing import List, Dict, Any
from django.db.models import Q
from django.contrib.postgres.search import TrigramSimilarity
from blog.models import BlogPost
from shop.models import Product
from core.logging_utils import get_logger

logger = get_logger(__name__)

class SearchService:
    """Business logic for search operations"""

    @staticmethod
    def search_blogs(query: str, threshold: float = 0.1, limit: int = 10) -> List[Dict]:
        """Search blog posts using trigram similarity"""
        blogs = (
            BlogPost.objects.live()
            .annotate(
                title_similarity=TrigramSimilarity('title', query),
                intro_similarity=TrigramSimilarity('intro', query),
            )
            .filter(
                Q(title_similarity__gt=threshold) |
                Q(intro_similarity__gt=threshold)
            )
            .select_related('header_image')
            .prefetch_related('categories', 'tags')
            .order_by('-title_similarity', '-intro_similarity')
            [:limit]
        )

        results = []
        for blog in blogs:
            # Get header image URL
            header_image_url = None
            if blog.header_image:
                try:
                    rendition = blog.header_image.get_rendition('fill-400x300')
                    header_image_url = rendition.url
                except Exception as e:
                    logger.warning(f"Failed to generate blog rendition: {e}")
                    header_image_url = blog.header_image.file.url if blog.header_image.file else None

            results.append({
                "id": blog.id,
                "title": blog.title,
                "slug": blog.slug,
                "intro": blog.intro,
                "header_image": header_image_url,
                "url": blog.url,
            })

        return results

    @staticmethod
    def search_products(query: str, threshold: float = 0.1, limit: int = 10) -> List[Dict]:
        """Search products using trigram similarity"""
        products = (
            Product.objects.filter(is_active=True, is_available=True, is_visible=True)
            .annotate(
                title_similarity=TrigramSimilarity('title', query),
                desc_similarity=TrigramSimilarity('description', query),
            )
            .filter(
                Q(title_similarity__gt=threshold) |
                Q(desc_similarity__gt=threshold)
            )
            .select_related('category')
            .prefetch_related('images')
            .order_by('-title_similarity', '-desc_similarity')
            [:limit]
        )

        results = []
        for product in products:
            # Use prefetched images
            images = list(product.images.all())
            feature_image = next((img for img in images if img.is_feature), None)
            if not feature_image and images:
                feature_image = images[0]

            feature_image_url = None
            if feature_image and feature_image.image:
                try:
                    rendition = feature_image.image.get_rendition('fill-400x300')
                    feature_image_url = rendition.url
                except Exception as e:
                    logger.warning(f"Failed to generate product rendition: {e}")
                    feature_image_url = feature_image.image.file.url

            results.append({
                "id": str(product.id),
                "title": product.title,
                "slug": product.slug,
                "price": float(product.price),
                "feature_image": feature_image_url,
            })

        return results

    @staticmethod
    def search_all(query: str, threshold: float = 0.1) -> Dict[str, Any]:
        """Perform global search across all content types"""
        if not query or len(query.strip()) < 2:
            return {"blog": [], "products": []}

        query = query.strip()

        logger.info(
            "Global search performed",
            extra={"extra_data": {
                "query": query,
                "threshold": threshold,
            }}
        )

        return {
            "blog": SearchService.search_blogs(query, threshold, limit=10),
            "products": SearchService.search_products(query, threshold, limit=10),
        }

# In core/views.py
from core.services.search import SearchService
from django.core.cache import cache
import hashlib

@api_view(['GET'])
@permission_classes([AllowAny])
def global_search(request):
    query = request.GET.get('q', '').strip()

    try:
        threshold = float(request.GET.get('threshold', 0.1))
        threshold = max(0.0, min(1.0, threshold))
    except (ValueError, TypeError):
        threshold = 0.1

    if not query:
        return Response({"results": {"blog": [], "products": []}})

    # Check cache
    cache_key = f"search:{hashlib.md5(f'{query}:{threshold}'.encode()).hexdigest()}"
    cached_results = cache.get(cache_key)

    if cached_results is not None:
        return Response(cached_results)

    # Perform search
    results = SearchService.search_all(query, threshold)

    # Cache results
    cache.set(cache_key, results, 300)

    return Response(results)
```

**Verification**:
```bash
# Test search
curl "http://localhost:8000/api/core/search/?q=test&threshold=0.1"

# Verify results format
{
    "blog": [...],
    "products": [...]
}

# Test caching - second request should be faster
time curl "http://localhost:8000/api/core/search/?q=test"

# Check logs
tail -f logs/derakht.log | grep "Global search"
```

---

### ✅ PR #24: Move Cart Total Calculation to Service
**Risk Level**: Medium
**Estimated Lines**: ~60 lines
**Dependencies**: PR #20 (CartService)

**Scope**: Replace Cart.total_amount property with database aggregation

**Files to Modify**:
- `shop/models/cart.py` (modify property)
- `shop/services/cart.py` (add calculation method)
- `shop/serializers/cart.py` (ensure uses optimized approach)

**Changes**:
```python
# In shop/services/cart.py
from django.db.models import Sum, F
from decimal import Decimal

class CartService:
    # ... existing methods

    @staticmethod
    def calculate_total(cart: Cart) -> Decimal:
        """Calculate cart total using database aggregation"""
        total = cart.items.aggregate(
            total=Sum(F('quantity') * F('product__price'))
        )['total'] or Decimal('0')

        discount = cart.discount_amount or Decimal('0')
        return total - discount

# In shop/models/cart.py
class Cart(BaseModel):
    # ... existing fields

    @property
    def total_amount(self):
        """
        Calculate cart total.
        Note: This triggers a query. For bulk operations, use
        CartService.calculate_total() with prefetched items.
        """
        from shop.services.cart import CartService
        return CartService.calculate_total(self)

    @property
    def item_count(self):
        """Get total number of items in cart"""
        from django.db.models import Sum
        count = self.items.aggregate(total=Sum('quantity'))['total']
        return count or 0

# In shop/serializers/cart.py
class CartDetailsSerializer(serializers.ModelSerializer):
    # When serializing multiple carts, annotate at queryset level:
    # carts = Cart.objects.annotate(
    #     total=Sum(F('items__quantity') * F('items__product__price'))
    # )

    total_amount = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()

    def get_total_amount(self, obj):
        # Use annotation if available, else calculate
        if hasattr(obj, 'total'):
            return obj.total
        from shop.services.cart import CartService
        return CartService.calculate_total(obj)

    def get_item_count(self, obj):
        if hasattr(obj, 'item_count_annotated'):
            return obj.item_count_annotated
        return obj.item_count
```

**Verification**:
```bash
# Test cart total calculation
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/shop/cart/

# Verify total is correct
# Add items and check total updates
curl -X POST -H "Authorization: Bearer <token>" \
  .../cart/add_item/ -d '{"product_id": "...", "quantity": 2}'

# Check query count - should use aggregation, not load all items
```

---

### ✅ PR #25: Move Order Total Calculation to Service
**Risk Level**: Medium
**Estimated Lines**: ~50 lines
**Dependencies**: PR #21 (OrderService)

**Scope**: Replace Order.calculate_total() with service method

**Files to Modify**:
- `shop/models/order.py` (deprecate method)
- `shop/services/order.py` (add to existing service)

**Changes**:
```python
# In shop/models/order.py
class Order(BaseModel):
    # ... existing fields

    def calculate_total(self):
        """
        DEPRECATED: Use OrderService.calculate_total() instead.
        This method will be removed in a future version.
        """
        import warnings
        warnings.warn(
            "Order.calculate_total() is deprecated. Use OrderService.calculate_total()",
            DeprecationWarning,
            stacklevel=2
        )
        from shop.services.order import OrderService
        total = OrderService.calculate_total(self)
        self.total_amount = total
        self.save()
        return total

# shop/services/order.py already has calculate_total from PR #21
# Just verify it's using aggregation properly

# Update any views/tasks that call order.calculate_total()
# to use OrderService.calculate_total(order) instead
```

**Verification**:
```bash
# Search for usage of order.calculate_total()
grep -r "\.calculate_total()" --include="*.py" shop/

# Update any found usages
# Test order total calculation
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/shop/orders/<order_id>/
```

---

### ✅ PR #26: Extract Phone Validation to Validators Module
**Risk Level**: Low
**Estimated Lines**: ~120 lines
**Dependencies**: None

**Scope**: Move phone validation from User.clean() to validators

**Files to Modify**:
- `users/validators.py` (create new file)
- `users/models.py` (use validator)
- `users/serializers.py` (use validator)

**Changes**:
```python
# Create users/validators.py
from django.core.exceptions import ValidationError
import re

def validate_iranian_phone(value: str) -> str:
    """
    Validate Iranian phone number format.
    Accepts: 09123456789 or +989123456789
    Returns: Normalized format (09123456789)
    """
    if not value:
        return value

    # Remove spaces and dashes
    phone = value.replace(' ', '').replace('-', '')

    # Pattern 1: 09123456789
    pattern1 = re.compile(r'^09\d{9}$')
    # Pattern 2: +989123456789
    pattern2 = re.compile(r'^\+989\d{9}$')
    # Pattern 3: 9123456789
    pattern3 = re.compile(r'^9\d{9}$')

    if pattern1.match(phone):
        return phone
    elif pattern2.match(phone):
        return '0' + phone[3:]  # Convert +989... to 09...
    elif pattern3.match(phone):
        return '0' + phone  # Convert 9... to 09...
    else:
        raise ValidationError(
            'شماره تلفن باید به فرمت 09123456789 باشد'
        )

# In users/models.py
from users.validators import validate_iranian_phone

class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    phone_number = models.CharField(
        _("Phone Number"),
        max_length=15,
        blank=True,
        null=True,
        validators=[validate_iranian_phone],  # Add validator
    )

    def clean(self):
        """Simplified clean method"""
        super().clean()
        # Phone validation now handled by validator
        # Keep any other validation here

# In users/serializers.py
from users.validators import validate_iranian_phone

class UserSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(
        required=False,
        allow_blank=True,
        validators=[validate_iranian_phone]
    )
```

**Verification**:
```bash
# Test phone validation
curl -X POST .../users/signup/ \
  -d '{"email": "test@test.com", "phone_number": "invalid", "password": "pass123"}'
# Should return validation error

curl -X POST .../users/signup/ \
  -d '{"email": "test@test.com", "phone_number": "09123456789", "password": "pass123"}'
# Should work

curl -X POST .../users/signup/ \
  -d '{"email": "test@test.com", "phone_number": "+989123456789", "password": "pass123"}'
# Should work and normalize to 09123456789
```

---

## Phase 5: Type Safety (PRs 27-30)

### ✅ PR #27: Add Type Hints to Service Layer
**Risk Level**: Low
**Estimated Lines**: ~120 lines
**Dependencies**: PRs #20-23 (service layer exists)

**Scope**: Add comprehensive type hints to all service methods

**Files to Modify**:
- `shop/services/cart.py`
- `shop/services/order.py`
- `shop/services/payment.py`
- `users/services/auth.py`
- `core/services/search.py`

**Changes**:
```python
# All service files should have complete type hints
from typing import Optional, Tuple, List, Dict, Any
from decimal import Decimal
from uuid import UUID

# Example for shop/services/cart.py
class CartService:
    @staticmethod
    def get_or_create_cart(
        user: Optional[User] = None,
        anonymous_id: Optional[UUID] = None
    ) -> Tuple[Cart, bool]:
        """Type hints already added in PR #20"""
        pass

    @staticmethod
    def add_item(
        cart: Cart,
        product: Product,
        quantity: int
    ) -> CartItem:
        """Type hints already added in PR #20"""
        pass

# Similar for all other service files
```

**Verification**:
```bash
# Install mypy
pip install mypy django-stubs djangorestframework-stubs

# Run type checking
mypy shop/services/
mypy users/services/
mypy core/services/

# Should show no errors
```

---

### ✅ PR #28: Add Type Hints to View Methods
**Risk Level**: Low
**Estimated Lines**: ~200 lines
**Dependencies**: None

**Scope**: Add type hints to view method signatures

**Files to Modify**:
- `shop/views/cart.py`
- `shop/views/order.py`
- `shop/views/payment.py`
- `shop/views/product.py`
- `users/views.py`
- `stories/views.py`
- `core/views.py`

**Changes**:
```python
from rest_framework.request import Request
from rest_framework.response import Response
from typing import Any, Optional
from uuid import UUID

# In shop/views/cart.py
class CartViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["post"])
    def add_item(self, request: Request) -> Response:
        # ... implementation
        pass

    @action(detail=False, methods=["get"])
    def get_cart(self, request: Request) -> Response:
        # ... implementation
        pass

# In shop/views/payment.py
class PaymentRequestView(APIView):
    def post(
        self,
        request: Request,
        order_id: Optional[UUID] = None
    ) -> Response:
        # ... implementation
        pass

# Similar for all view files
```

**Verification**:
```bash
# Run mypy on views
mypy shop/views/
mypy users/views.py
mypy core/views.py

# Check for type errors
```

---

### ✅ PR #29: Create TypedDict for Payment Responses
**Risk Level**: Low
**Estimated Lines**: ~80 lines
**Dependencies**: None

**Scope**: Replace Dict[str, Any] with proper TypedDict definitions

**Files to Modify**:
- `shop/services/payment.py`
- `shop/gateways/base.py`
- `shop/gateways/zarinpal_sdk.py`

**Changes**:
```python
# In shop/services/payment.py
from typing import TypedDict, Optional, Literal
from decimal import Decimal
from uuid import UUID

class PaymentRequestResult(TypedDict):
    success: bool
    payment_url: str
    payment_id: UUID
    gateway: str
    authority: Optional[str]
    error_message: Optional[str]

class PaymentVerificationResult(TypedDict):
    success: bool
    reference_id: Optional[str]
    status: Literal['COMPLETED', 'FAILED', 'PENDING']
    amount: Decimal
    error_message: Optional[str]

# In shop/gateways/base.py
from abc import ABC, abstractmethod

class BasePaymentGateway(ABC):
    @abstractmethod
    def request_payment(
        self,
        order: Order
    ) -> PaymentRequestResult:
        """Request payment from gateway"""
        pass

    @abstractmethod
    def verify_payment(
        self,
        payment: Payment,
        authority: str
    ) -> PaymentVerificationResult:
        """Verify payment with gateway"""
        pass

# Update implementations to return typed dictionaries
```

**Verification**:
```bash
# Run mypy
mypy shop/services/payment.py
mypy shop/gateways/

# Test payment flow still works
curl -X POST .../payments/request/<order_id>/
```

---

### ✅ PR #30: Add Request/Response Schema Documentation
**Risk Level**: Low
**Estimated Lines**: ~150 lines
**Dependencies**: None

**Scope**: Add drf-spectacular for OpenAPI schema generation

**Files to Modify**:
- `requirements.txt` (add drf-spectacular)
- `derakht/settings.py` (configure spectacular)
- `derakht/urls.py` (add schema URLs)
- Add schema decorators to key endpoints

**Changes**:
```python
# In requirements.txt
drf-spectacular==0.27.0

# In derakht/settings.py
INSTALLED_APPS = [
    # ...
    'drf_spectacular',
]

REST_FRAMEWORK = {
    # ...
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Derakht API',
    'DESCRIPTION': 'Persian educational platform API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# In derakht/urls.py
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # ...
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# In shop/views/cart.py - add examples
from drf_spectacular.utils import extend_schema, OpenApiExample

class CartViewSet(viewsets.ViewSet):
    @extend_schema(
        request=AddCartItemSerializer,
        responses={201: CartItemSerializer},
        examples=[
            OpenApiExample(
                'Add Item Example',
                value={
                    'product_id': '123e4567-e89b-12d3-a456-426614174000',
                    'quantity': 2,
                },
            ),
        ],
    )
    @action(detail=False, methods=["post"])
    def add_item(self, request: Request) -> Response:
        # ... implementation
        pass
```

**Verification**:
```bash
# Install dependencies
poetry add drf-spectacular

# Generate schema
python manage.py spectacular --file schema.yml

# Start server and visit
open http://localhost:8000/api/docs/

# Should see interactive API documentation
```

---

## Phase 6: Testing (PRs 31-33)

### ✅ PR #31: Set Up Test Infrastructure
**Risk Level**: Low
**Estimated Lines**: ~200 lines
**Dependencies**: None

**Scope**: Create test base classes, fixtures, and configuration

**Files to Modify**:
- `shop/tests/__init__.py` (create)
- `shop/tests/base.py` (create)
- `shop/tests/fixtures.py` (create)
- `derakht/settings_test.py` (create)
- `pytest.ini` (create)

**Changes**:
```python
# Create shop/tests/__init__.py
# Empty file

# Create shop/tests/base.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from shop.models import Product, Category, Cart
from decimal import Decimal

User = get_user_model()

class ShopTestCase(TestCase):
    """Base test case with common fixtures"""

    def setUp(self):
        """Set up test fixtures"""
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
        )

        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category',
        )

        # Create test products
        self.product1 = Product.objects.create(
            title='Test Product 1',
            slug='test-product-1',
            description='Test description',
            price=Decimal('100.00'),
            category=self.category,
            is_available=True,
            is_visible=True,
        )

        self.product2 = Product.objects.create(
            title='Test Product 2',
            slug='test-product-2',
            description='Test description 2',
            price=Decimal('200.00'),
            category=self.category,
            is_available=True,
            is_visible=True,
        )

    def create_cart(self, user=None, anonymous_id=None):
        """Helper to create test cart"""
        return Cart.objects.create(
            user=user,
            anonymous_id=anonymous_id,
            status='ACTIVE',
        )

# Create shop/tests/fixtures.py
import pytest
from django.contrib.auth import get_user_model
from shop.models import Product, Category
from decimal import Decimal

User = get_user_model()

@pytest.fixture
def user():
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123',
    )

@pytest.fixture
def category():
    return Category.objects.create(
        name='Test Category',
        slug='test-category',
    )

@pytest.fixture
def product(category):
    return Product.objects.create(
        title='Test Product',
        slug='test-product',
        price=Decimal('100.00'),
        category=category,
        is_available=True,
        is_visible=True,
    )

# Create derakht/settings_test.py
from .settings import *

# Use in-memory database for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Use in-memory cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Use console email backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable logging in tests
LOGGING = {}

# Fast password hasher for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Create pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = derakht.settings_test
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --reuse-db --nomigrations
```

**Verification**:
```bash
# Install pytest
poetry add --dev pytest pytest-django

# Run tests
pytest shop/tests/

# Should show tests collected (even if none exist yet)
```

---

### ✅ PR #32: Add Cart Service Tests
**Risk Level**: Medium
**Estimated Lines**: ~300 lines
**Dependencies**: PR #31 (test infrastructure), PR #20 (CartService)

**Scope**: Comprehensive tests for CartService

**Files to Modify**:
- `shop/tests/test_cart_service.py` (create)

**Changes**:
```python
# Create shop/tests/test_cart_service.py
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from shop.models import Cart, Product, Category, PromoCode, CartItem
from shop.services.cart import CartService
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()

class CartServiceTestCase(TestCase):
    """Tests for CartService"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
        )

        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category',
        )

        self.product = Product.objects.create(
            title='Test Product',
            slug='test-product',
            price=Decimal('100.00'),
            category=self.category,
            is_available=True,
            is_visible=True,
        )

    def test_get_or_create_cart_for_user(self):
        """Test creating cart for authenticated user"""
        cart, created = CartService.get_or_create_cart(user=self.user)

        self.assertTrue(created)
        self.assertEqual(cart.user, self.user)
        self.assertEqual(cart.status, 'ACTIVE')

        # Getting again should return same cart
        cart2, created2 = CartService.get_or_create_cart(user=self.user)
        self.assertFalse(created2)
        self.assertEqual(cart.id, cart2.id)

    def test_get_or_create_cart_anonymous(self):
        """Test creating cart for anonymous user"""
        import uuid
        anon_id = uuid.uuid4()

        cart, created = CartService.get_or_create_cart(anonymous_id=anon_id)

        self.assertTrue(created)
        self.assertEqual(cart.anonymous_id, anon_id)
        self.assertIsNone(cart.user)

    def test_add_item_to_cart(self):
        """Test adding item to cart"""
        cart, _ = CartService.get_or_create_cart(user=self.user)

        cart_item = CartService.add_item(cart, self.product, 2)

        self.assertEqual(cart_item.cart, cart)
        self.assertEqual(cart_item.product, self.product)
        self.assertEqual(cart_item.quantity, 2)

    def test_add_item_increases_quantity(self):
        """Test adding same item increases quantity"""
        cart, _ = CartService.get_or_create_cart(user=self.user)

        CartService.add_item(cart, self.product, 2)
        cart_item = CartService.add_item(cart, self.product, 3)

        self.assertEqual(cart_item.quantity, 5)

    def test_add_unavailable_product_fails(self):
        """Test adding unavailable product raises error"""
        cart, _ = CartService.get_or_create_cart(user=self.user)
        self.product.is_available = False
        self.product.save()

        with self.assertRaises(ValueError) as cm:
            CartService.add_item(cart, self.product, 1)

        self.assertIn("not available", str(cm.exception))

    def test_update_quantity(self):
        """Test updating item quantity"""
        cart, _ = CartService.get_or_create_cart(user=self.user)
        CartService.add_item(cart, self.product, 2)

        cart_item = CartService.update_quantity(cart, self.product, 5)

        self.assertEqual(cart_item.quantity, 5)

    def test_update_quantity_to_zero_removes_item(self):
        """Test updating quantity to 0 removes item"""
        cart, _ = CartService.get_or_create_cart(user=self.user)
        CartService.add_item(cart, self.product, 2)

        result = CartService.update_quantity(cart, self.product, 0)

        self.assertIsNone(result)
        self.assertEqual(cart.items.count(), 0)

    def test_apply_valid_promo_code(self):
        """Test applying valid promo code"""
        cart, _ = CartService.get_or_create_cart(user=self.user)
        CartService.add_item(cart, self.product, 2)  # Total: 200

        promo = PromoCode.objects.create(
            code='SUMMER10',
            discount_type='percentage',
            discount_value=10,
            min_purchase=Decimal('100.00'),
            valid_from=timezone.now() - timedelta(days=1),
            valid_to=timezone.now() + timedelta(days=7),
            is_active=True,
        )

        promo_returned, discount = CartService.apply_promo_code(cart, 'SUMMER10')

        self.assertEqual(promo_returned, promo)
        self.assertEqual(discount, Decimal('20.00'))  # 10% of 200

        cart.refresh_from_db()
        self.assertEqual(cart.promo_code, promo)
        self.assertEqual(cart.discount_amount, Decimal('20.00'))

    def test_apply_invalid_promo_code_fails(self):
        """Test applying invalid promo code raises error"""
        cart, _ = CartService.get_or_create_cart(user=self.user)

        with self.assertRaises(ValueError) as cm:
            CartService.apply_promo_code(cart, 'INVALID')

        self.assertIn("Invalid or expired", str(cm.exception))

    def test_apply_promo_below_minimum_fails(self):
        """Test applying promo code below minimum purchase fails"""
        cart, _ = CartService.get_or_create_cart(user=self.user)
        CartService.add_item(cart, self.product, 1)  # Total: 100

        promo = PromoCode.objects.create(
            code='BIG50',
            discount_type='percentage',
            discount_value=50,
            min_purchase=Decimal('500.00'),
            valid_from=timezone.now() - timedelta(days=1),
            valid_to=timezone.now() + timedelta(days=7),
            is_active=True,
        )

        with self.assertRaises(ValueError) as cm:
            CartService.apply_promo_code(cart, 'BIG50')

        self.assertIn("Minimum purchase", str(cm.exception))

    def test_calculate_total(self):
        """Test cart total calculation"""
        cart, _ = CartService.get_or_create_cart(user=self.user)
        CartService.add_item(cart, self.product, 2)  # 200

        total = CartService.calculate_total(cart)
        self.assertEqual(total, Decimal('200.00'))

        # With discount
        cart.discount_amount = Decimal('20.00')
        cart.save()

        total = CartService.calculate_total(cart)
        self.assertEqual(total, Decimal('180.00'))
```

**Verification**:
```bash
# Run cart service tests
pytest shop/tests/test_cart_service.py -v

# Should show all tests passing
# Check coverage
pytest --cov=shop.services.cart shop/tests/test_cart_service.py
```

---

### ✅ PR #33: Add Payment Service Tests
**Risk Level**: Medium
**Estimated Lines**: ~250 lines
**Dependencies**: PR #31 (test infrastructure)

**Scope**: Tests for payment service with mocked gateway

**Files to Modify**:
- `shop/tests/test_payment_service.py` (create)
- `shop/tests/mocks.py` (create mock gateway)

**Changes**:
```python
# Create shop/tests/mocks.py
from shop.gateways.base import BasePaymentGateway
from shop.models import Order, Payment
from decimal import Decimal
from uuid import uuid4

class MockPaymentGateway(BasePaymentGateway):
    """Mock payment gateway for testing"""

    def __init__(self):
        self.should_succeed = True
        self.payment_url = "https://mock-gateway.com/pay/12345"
        self.authority = "A00000000000000000000000000012345678"
        self.reference_id = "REF123456"

    def request_payment(self, order: Order):
        if self.should_succeed:
            return {
                "success": True,
                "payment_url": self.payment_url,
                "authority": self.authority,
                "payment_id": uuid4(),
                "gateway": "mock",
            }
        else:
            return {
                "success": False,
                "error_message": "Mock gateway error",
            }

    def verify_payment(self, payment: Payment, authority: str):
        if self.should_succeed and authority == self.authority:
            return {
                "success": True,
                "reference_id": self.reference_id,
                "status": "COMPLETED",
                "amount": payment.amount,
            }
        else:
            return {
                "success": False,
                "error_message": "Verification failed",
                "status": "FAILED",
            }

# Create shop/tests/test_payment_service.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from shop.models import Order, Product, Category, OrderItem, Payment
from shop.services.payment import PaymentService
from shop.tests.mocks import MockPaymentGateway
from decimal import Decimal
from unittest.mock import patch

User = get_user_model()

class PaymentServiceTestCase(TestCase):
    """Tests for PaymentService"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
        )

        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category',
        )

        self.product = Product.objects.create(
            title='Test Product',
            slug='test-product',
            price=Decimal('100.00'),
            category=self.category,
        )

        # Create test order
        self.order = Order.objects.create(
            user=self.user,
            status='PENDING',
            total_amount=Decimal('200.00'),
        )

        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=Decimal('100.00'),
        )

    @patch('shop.services.payment.PaymentGatewayFactory.get_gateway')
    def test_request_payment_success(self, mock_get_gateway):
        """Test successful payment request"""
        mock_gateway = MockPaymentGateway()
        mock_get_gateway.return_value = mock_gateway

        result = PaymentService.request_payment(self.order)

        self.assertTrue(result['success'])
        self.assertIn('payment_url', result)
        self.assertIn('authority', result)

        # Check payment record created
        payment = Payment.objects.filter(order=self.order).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, self.order.total_amount)
        self.assertEqual(payment.status, 'PENDING')

    @patch('shop.services.payment.PaymentGatewayFactory.get_gateway')
    def test_request_payment_failure(self, mock_get_gateway):
        """Test failed payment request"""
        mock_gateway = MockPaymentGateway()
        mock_gateway.should_succeed = False
        mock_get_gateway.return_value = mock_gateway

        result = PaymentService.request_payment(self.order)

        self.assertFalse(result['success'])
        self.assertIn('error_message', result)

    @patch('shop.services.payment.PaymentGatewayFactory.get_gateway')
    def test_verify_payment_success(self, mock_get_gateway):
        """Test successful payment verification"""
        mock_gateway = MockPaymentGateway()
        mock_get_gateway.return_value = mock_gateway

        # Create payment
        payment = Payment.objects.create(
            order=self.order,
            amount=self.order.total_amount,
            gateway='mock',
            status='PENDING',
        )

        result = PaymentService.verify_payment(
            payment,
            mock_gateway.authority
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'COMPLETED')

        # Check payment updated
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'COMPLETED')
        self.assertEqual(payment.reference_id, mock_gateway.reference_id)

        # Check order updated
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'PROCESSING')
```

**Verification**:
```bash
# Run payment tests
pytest shop/tests/test_payment_service.py -v

# Check coverage
pytest --cov=shop.services.payment shop/tests/test_payment_service.py

# Run all shop tests
pytest shop/tests/ -v
```

---

## Phase 7: API Consistency (PRs 34-35)

### ✅ PR #34: Standardize Error Response Format
**Risk Level**: HIGH - Affects frontend
**Estimated Lines**: ~300 lines
**Dependencies**: All previous PRs (touches many files)

**⚠️ IMPORTANT**: Coordinate with frontend team before merging!

**Scope**: Standardize all error responses to single format

**Files to Modify**:
- `core/exceptions.py` (create custom exception handler)
- `derakht/settings.py` (configure exception handler)
- All view files (update error responses)

**Changes**:
```python
# Create core/exceptions.py
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

# In derakht/settings.py
REST_FRAMEWORK = {
    # ... existing config
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
}

# Update view error responses to use standard format
# Example in shop/views/cart.py:
from rest_framework.exceptions import ValidationError

@action(detail=False, methods=["post"])
def add_item(self, request):
    try:
        # ... logic
        if not product.is_available:
            raise ValidationError({
                "code": "PRODUCT_UNAVAILABLE",
                "message": "این محصول در حال حاضر موجود نیست",
            })
    except ValueError as e:
        raise ValidationError({
            "code": "INVALID_REQUEST",
            "message": str(e),
        })
```

**Migration Strategy**:
1. Deploy this PR to staging first
2. Update frontend to handle new error format
3. Test all error scenarios in staging
4. Deploy to production with frontend changes

**Verification**:
```bash
# Test various error scenarios
# 1. Validation error
curl -X POST .../cart/add_item/ -d '{}'
# Should return:
# {
#   "error": {
#     "code": "VALIDATION_ERROR",
#     "message": "...",
#     "details": {"product_id": ["این فیلد الزامی است"]}
#   }
# }

# 2. Authentication error
curl .../orders/
# Should return:
# {
#   "error": {
#     "code": "NOT_AUTHENTICATED",
#     "message": "لطفا وارد شوید",
#     "details": {}
#   }
# }

# 3. Not found
curl .../products/invalid-uuid/
# Should return:
# {
#   "error": {
#     "code": "NOT_FOUND",
#     "message": "یافت نشد",
#     "details": {}
#   }
# }
```

---

### ✅ PR #35: Convert Error Messages to Persian
**Risk Level**: Medium
**Estimated Lines**: ~200 lines
**Dependencies**: PR #34 (error format standardized)

**Scope**: Replace all English error messages with Persian

**Files to Modify**:
- `shop/views/cart.py`
- `shop/views/payment.py`
- `users/views.py`
- `stories/views.py`
- All serializers

**Changes**:
```python
# Create a constants file for error messages
# core/messages.py
class ErrorMessages:
    """Persian error messages"""

    # Cart errors
    CART_EMPTY = "سبد خرید خالی است"
    CART_INVALID = "سبد خرید معتبر نیست"
    PRODUCT_UNAVAILABLE = "این محصول در حال حاضر موجود نیست"
    PRODUCT_OUT_OF_STOCK = "موجودی این محصول کافی نیست"
    QUANTITY_INVALID = "تعداد باید عدد مثبت باشد"

    # Promo code errors
    PROMO_INVALID = "کد تخفیف نامعتبر یا منقضی شده است"
    PROMO_MIN_PURCHASE = "حداقل مبلغ خرید برای این کد تخفیف {min_amount} تومان است"
    PROMO_MAX_USES = "این کد تخفیف به حداکثر تعداد استفاده رسیده است"

    # Payment errors
    PAYMENT_FAILED = "پرداخت با خطا مواجه شد"
    PAYMENT_INVALID = "اطلاعات پرداخت معتبر نیست"
    PAYMENT_AMOUNT_MISMATCH = "مبلغ پرداخت با سفارش مطابقت ندارد"

    # Order errors
    ORDER_NOT_FOUND = "سفارش یافت نشد"
    ORDER_NOT_PENDING = "این سفارش قابل پرداخت نیست"

    # Auth errors
    EMAIL_EXISTS = "این ایمیل قبلا ثبت شده است"
    INVALID_CREDENTIALS = "ایمیل یا رمز عبور اشتباه است"
    PASSWORD_WEAK = "رمز عبور باید حداقل ۸ کاراکتر باشد"

    # General
    INTERNAL_ERROR = "خطای سرور. لطفا بعدا تلاش کنید"
    INVALID_REQUEST = "درخواست نامعتبر است"
    PERMISSION_DENIED = "شما مجوز دسترسی به این بخش را ندارید"
    NOT_FOUND = "یافت نشد"

# Update views to use constants
# In shop/views/cart.py
from core.messages import ErrorMessages

@action(detail=False, methods=["post"])
def add_item(self, request):
    # ... logic
    if not product.is_available:
        raise ValidationError({
            "code": "PRODUCT_UNAVAILABLE",
            "message": ErrorMessages.PRODUCT_UNAVAILABLE,
        })

    if quantity < 1:
        raise ValidationError({
            "code": "QUANTITY_INVALID",
            "message": ErrorMessages.QUANTITY_INVALID,
        })

# Update serializers
# In shop/serializers/cart.py
class AddCartItemSerializer(serializers.Serializer):
    product_id = serializers.UUIDField(
        error_messages={
            'required': 'شناسه محصول الزامی است',
            'invalid': 'شناسه محصول معتبر نیست',
        }
    )
    quantity = serializers.IntegerField(
        min_value=1,
        error_messages={
            'required': 'تعداد الزامی است',
            'invalid': 'تعداد باید عدد باشد',
            'min_value': 'تعداد باید حداقل ۱ باشد',
        }
    )
```

**Verification**:
```bash
# Test all error messages are in Persian
# Create a script to test all endpoints
python manage.py shell

from django.test import Client
client = Client()

# Test various errors and check messages are Persian
response = client.post('/api/shop/cart/add_item/', {})
print(response.json())
# Should show Persian errors

# Grep for English error messages
grep -r '"error":.*[A-Za-z]' --include="*.py" shop/views/
grep -r "error_messages.*[A-Za-z]" --include="*.py" shop/serializers/
# Should find minimal English (only in code, not user-facing)
```

---

## Summary

**Total PRs**: 35
**Phases**: 7
**Risk Distribution**:
- Low Risk: 20 PRs
- Medium Risk: 13 PRs
- High Risk: 2 PRs (PRs #34, #35 - coordinate with frontend)

**Dependencies**: Most PRs are independent. Key dependency chains:
- Service layer PRs (20-26) depend on each other loosely
- Testing PRs (32-33) depend on PR #31
- Error standardization (35) depends on PR #34

**Estimated Timeline**: 6-8 weeks at 1-2 PRs per day

**Critical Path**:
1. Security fixes (PRs 1-6) - Week 1
2. Performance database (PRs 9-19) - Weeks 2-3
3. Code organization (PRs 20-26) - Weeks 4-5
4. Testing (PRs 31-33) - Week 6
5. API consistency (PRs 34-35) - Week 7 (coordinate with frontend)

**How to Use This Plan**:
1. Work through PRs sequentially by number
2. Each PR is self-contained and can be merged independently
3. Run verification steps before creating PR
4. Get code review before merging
5. Deploy to staging and test before production
6. Update this checklist as you complete each PR

**Next Steps**:
1. Review this plan with the team
2. Set up project board with these PRs as issues
3. Start with PR #1 (lowest risk, high value)
4. Maintain this document as you progress
