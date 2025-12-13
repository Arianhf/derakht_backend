# Comprehensive Testing Strategy for Derakht Backend

## Executive Summary

This document outlines a complete testing strategy for the Derakht Django backend, targeting **90% code coverage** with a focus on critical business logic: payment processing, order management, and authentication flows.

### Recommended Approach
- **Framework**: pytest + pytest-django (already in requirements)
- **Coverage Tool**: pytest-cov
- **Mocking**: responses, requests-mock (already available), factory_boy for fixtures
- **API Testing**: Django REST Framework's APIClient
- **Database**: PostgreSQL with transaction rollback for test isolation
- **Async Testing**: pytest-asyncio (if needed for background tasks)

### Testing Pyramid Distribution
```
    /\
   /E2E\      10% - End-to-end flows (checkout, payment verification)
  /------\
 /  INT   \   30% - Integration tests (API endpoints, database interactions)
/----------\
/   UNIT    \ 60% - Unit tests (models, serializers, utilities, business logic)
```

---

## 1. Testing Framework & Tools

### Core Testing Stack

| Tool | Purpose | Justification |
|------|---------|---------------|
| **pytest** | Test runner | More Pythonic than unittest, powerful fixtures, plugins |
| **pytest-django** | Django integration | Database setup, fixtures, settings management |
| **pytest-cov** | Coverage reporting | Line and branch coverage with HTML reports |
| **factory_boy** | Test data generation | DRY fixture creation, complex object graphs |
| **Faker** | Realistic fake data | Generate phone numbers, emails, names |
| **freezegun** | Time mocking | Test date-based logic (promos, orders) |
| **responses** | HTTP mocking | Mock Zarinpal API responses |
| **pytest-xdist** | Parallel testing | Speed up test suite execution |

### Additional Tools for Specific Scenarios

- **django-silk**: Query profiling (identify N+1 queries during tests)
- **pytest-benchmark**: Performance regression tests
- **pytest-randomly**: Detect order-dependent tests
- **hypothesis**: Property-based testing for edge cases

---

## 2. Project Structure

```
derakht_backend/
├── pytest.ini                          # pytest configuration
├── conftest.py                         # Global fixtures and test configuration
├── .coveragerc                         # Coverage configuration
├── requirements-test.txt               # Test-specific dependencies
│
├── shop/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                 # Shop-specific fixtures
│   │   ├── factories.py                # Factory Boy factories
│   │   │
│   │   ├── unit/
│   │   │   ├── test_models.py          # Product, Order, Cart models
│   │   │   ├── test_serializers.py     # Serializer validation
│   │   │   ├── test_order_management.py # State machine logic
│   │   │   ├── test_payment_service.py # Payment business logic
│   │   │   └── test_signals.py         # Signal handlers
│   │   │
│   │   ├── integration/
│   │   │   ├── test_product_api.py     # Product endpoints
│   │   │   ├── test_cart_api.py        # Cart operations
│   │   │   ├── test_order_api.py       # Order lifecycle
│   │   │   ├── test_payment_api.py     # Payment integration
│   │   │   └── test_promo_codes.py     # Discount logic
│   │   │
│   │   └── e2e/
│   │       ├── test_checkout_flow.py   # Browse → Cart → Checkout → Payment
│   │       └── test_order_fulfillment.py # Order → Payment → Delivery
│   │
├── users/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── factories.py
│   │   ├── unit/
│   │   │   ├── test_models.py          # User, Address models
│   │   │   ├── test_validators.py      # Phone number validation
│   │   │   └── test_serializers.py
│   │   │
│   │   ├── integration/
│   │   │   ├── test_auth_api.py        # Signup, login, JWT
│   │   │   ├── test_profile_api.py     # Profile updates
│   │   │   ├── test_address_api.py     # Address CRUD
│   │   │   └── test_password_reset.py  # Password reset flow
│   │   │
│   │   └── e2e/
│   │       └── test_user_registration.py # Full signup → verify → login
│   │
├── stories/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── factories.py
│   │   ├── unit/
│   │   │   ├── test_models.py          # Story, StoryPart models
│   │   │   └── test_validators.py      # Hex color validation
│   │   │
│   │   ├── integration/
│   │   │   ├── test_story_api.py       # Story CRUD
│   │   │   ├── test_template_api.py    # Template selection
│   │   │   └── test_asset_upload.py    # Image uploads
│   │   │
│   │   └── e2e/
│   │       └── test_story_creation.py  # Template → Parts → Complete
│   │
├── blog/
│   ├── tests/
│   │   ├── unit/
│   │   │   └── test_models.py          # BlogPost, schema markup
│   │   │
│   │   └── integration/
│   │       └── test_wagtail_api.py     # Wagtail endpoints
│   │
└── core/
    ├── tests/
    │   ├── unit/
    │   │   └── test_feature_flags.py
    │   │
    │   └── integration/
    │       └── test_search_api.py
```

---

## 3. Critical Test Coverage Priorities

### Phase 1: Foundation (Week 1-2) - Critical Business Logic

**Priority 1A: Payment Processing** ⚠️ HIGHEST RISK
- ✅ Payment gateway integration (Zarinpal mocking)
- ✅ Payment request/verification flow
- ✅ Transaction logging
- ✅ Invoice generation on payment completion
- ✅ Payment callback handling
- ✅ Manual payment receipt upload

**Priority 1B: Order Management** 🔴 CRITICAL PATH
- ✅ Order state machine transitions
- ✅ Invalid state changes should fail
- ✅ Order status history tracking
- ✅ Order cancellation rules
- ✅ Order total calculation
- ✅ Shipping info creation

**Priority 1C: Authentication & Authorization** 🔒 SECURITY
- ✅ User signup with email validation
- ✅ JWT token generation and refresh
- ✅ Email verification
- ✅ Password reset flow
- ✅ Profile image upload/delete
- ✅ Permission checks (ownership validation)

### Phase 2: Core Features (Week 3-4)

**Priority 2A: Cart Operations**
- ✅ Anonymous cart creation (UUID-based)
- ✅ Authenticated cart operations
- ✅ Cart merging on login
- ✅ Stock validation on add to cart
- ✅ Quantity updates (zero removes item)
- ✅ Promo code application and discount calculation
- ✅ Checkout to order conversion

**Priority 2B: Product & Inventory**
- ✅ Product filtering (age, category, price)
- ✅ Stock availability checks
- ✅ Feature image selection
- ✅ Category hierarchy
- ✅ QR code lookup

**Priority 2C: Story Creation**
- ✅ Story creation from templates
- ✅ Story part updates (text, illustration, canvas)
- ✅ Status transitions (DRAFT → COMPLETED)
- ✅ Image asset management
- ✅ Color customization validation

### Phase 3: Extended Features (Week 5-6)

**Priority 3A: User Management**
- ✅ Address CRUD operations
- ✅ Default address enforcement
- ✅ Phone number validation (Iranian)
- ✅ Profile updates

**Priority 3B: Content Management**
- ✅ Blog post publishing
- ✅ SEO field validation
- ✅ Schema markup generation
- ✅ Tag and category management

**Priority 3C: Edge Cases & Performance**
- ✅ Concurrent cart updates
- ✅ Race conditions in order creation
- ✅ Payment timeout handling
- ✅ Large file upload handling
- ✅ Database query optimization (N+1 detection)

---

## 4. Testing Patterns & Best Practices

### 4.1 Test Organization Pattern: AAA (Arrange-Act-Assert)

```python
def test_add_product_to_cart(authenticated_client, product_factory):
    # Arrange - Set up test data
    product = product_factory(stock=10, price=Decimal('99.99'))

    # Act - Perform the action
    response = authenticated_client.post('/api/shop/cart/add_item/', {
        'product_id': product.id,
        'quantity': 2
    })

    # Assert - Verify outcomes
    assert response.status_code == 200
    assert Cart.objects.filter(user=authenticated_client.user).exists()
    assert CartItem.objects.get(product=product).quantity == 2
```

### 4.2 Fixture Strategy

**Global Fixtures** (`conftest.py` at root):
- Database setup with transaction rollback
- API clients (authenticated, anonymous)
- Mock external services (Zarinpal, email)

**App-Specific Fixtures** (per-app `conftest.py`):
- Common test objects (users, products, orders)
- Reusable test utilities

**Factory Boy Factories** (`factories.py`):
- Object creation with sensible defaults
- Relationship handling
- Sequence generation for unique fields

### 4.3 Database Testing Strategy

**Approach**: Use real PostgreSQL with transaction rollback (not SQLite)

**Why?**
- Ensures tests match production behavior
- Tests database constraints and triggers
- Validates PostgreSQL-specific features (JSON fields, etc.)

**Setup**:
```python
# pytest.ini
[tool:pytest]
DJANGO_SETTINGS_MODULE = derakht.settings_test
```

```python
# settings_test.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'test_derakht',
        'ATOMIC_REQUESTS': True,  # Auto-rollback
    }
}
```

### 4.4 Mocking External Services

**Zarinpal Payment Gateway**:
```python
import responses

@responses.activate
def test_zarinpal_payment_request(order):
    responses.add(
        responses.POST,
        'https://payment.zarinpal.com/pg/v4/payment/request.json',
        json={'data': {'authority': 'A00000000000000000000000000123456'}, 'errors': []},
        status=200
    )

    service = PaymentService()
    result = service.request_payment(order, 'zarinpal')

    assert result['authority'] == 'A00000000000000000000000000123456'
```

**Email Sending**:
```python
from django.core import mail

def test_password_reset_email_sent(client, user):
    response = client.post('/api/users/request-password-reset/', {
        'email': user.email
    })

    assert len(mail.outbox) == 1
    assert user.email in mail.outbox[0].to
    assert 'Reset Password' in mail.outbox[0].subject
```

### 4.5 Parameterized Testing

```python
import pytest

@pytest.mark.parametrize('initial_status,target_status,should_succeed', [
    ('CART', 'PENDING', True),
    ('PENDING', 'PROCESSING', True),
    ('PROCESSING', 'CONFIRMED', True),
    ('CART', 'CONFIRMED', False),  # Invalid jump
    ('DELIVERED', 'PROCESSING', False),  # Backward invalid
])
def test_order_status_transitions(order_factory, initial_status, target_status, should_succeed):
    order = order_factory(status=initial_status)

    if should_succeed:
        order.transition_to(target_status)
        assert order.status == target_status
    else:
        with pytest.raises(ValidationError):
            order.transition_to(target_status)
```

### 4.6 Testing Async Operations

```python
import pytest

@pytest.mark.asyncio
async def test_background_invoice_generation(order_with_payment):
    # Trigger payment completion signal
    order_with_payment.payment.status = 'completed'
    order_with_payment.payment.save()

    # Allow signal handlers to process
    await asyncio.sleep(0.1)

    # Verify invoice created
    assert Invoice.objects.filter(order=order_with_payment).exists()
```

---

## 5. Coverage Goals & Metrics

### Target Coverage by Component

| Component | Target Coverage | Priority | Rationale |
|-----------|----------------|----------|-----------|
| **Payment Processing** | 95%+ | P0 | Financial transactions - zero tolerance for bugs |
| **Order State Machine** | 95%+ | P0 | Business-critical logic |
| **Authentication** | 90%+ | P0 | Security-critical |
| **Cart Operations** | 90%+ | P1 | Core user experience |
| **Product API** | 85%+ | P1 | High traffic, customer-facing |
| **Story Creation** | 80%+ | P1 | Unique feature, complex logic |
| **Models** | 85%+ | P1 | Data integrity |
| **Serializers** | 80%+ | P2 | API validation |
| **Views** | 75%+ | P2 | Already covered by integration tests |
| **Signals** | 90%+ | P2 | Side effects must be tested |

### Exclusions from Coverage
- Migrations
- `__init__.py` files
- Admin configurations
- Settings files
- Development utilities

### Coverage Configuration (`.coveragerc`)
```ini
[run]
source = .
omit =
    */migrations/*
    */tests/*
    */admin.py
    manage.py
    derakht/settings*.py
    */venv/*
    */virtualenv/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    def __str__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod
```

---

## 6. CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test_derakht
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_derakht
        run: |
          pytest --cov=. --cov-report=xml --cov-report=html --cov-report=term-missing

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          fail_ci_if_error: true

      - name: Check coverage threshold
        run: |
          pytest --cov=. --cov-fail-under=80
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        args: ['-v', '--tb=short']
```

---

## 7. Common Pitfalls & Solutions

### Pitfall 1: Test Database Not Isolated
**Problem**: Tests fail intermittently due to shared state
**Solution**: Use `@pytest.mark.django_db(transaction=True)` and ensure proper teardown

### Pitfall 2: Hardcoded Timestamps
**Problem**: Date-based tests fail at different times
**Solution**: Use `freezegun` to mock time
```python
from freezegun import freeze_time

@freeze_time("2025-01-15 12:00:00")
def test_promo_code_expiry(promo_code):
    assert promo_code.is_valid()
```

### Pitfall 3: Order-Dependent Tests
**Problem**: Tests pass individually but fail when run together
**Solution**: Use `pytest-randomly` to detect, ensure proper isolation

### Pitfall 4: Slow Test Suite
**Problem**: Full suite takes too long (>5 minutes)
**Solution**:
- Use `pytest-xdist` for parallel execution: `pytest -n auto`
- Profile slow tests: `pytest --durations=10`
- Mock external services aggressively

### Pitfall 5: Incomplete Mock Coverage
**Problem**: Tests make real API calls to Zarinpal
**Solution**: Use `responses` library and fail on unmocked requests
```python
@responses.activate
def test_payment_flow():
    responses.assert_all_requests_are_fired = True
    # Test code...
```

### Pitfall 6: Factory Circular Dependencies
**Problem**: Factory Boy creates infinite loops
**Solution**: Use `factory.PostGeneration` or `factory.LazyAttribute`

### Pitfall 7: File Upload Tests
**Problem**: Media files persist between tests
**Solution**: Use `override_settings(MEDIA_ROOT=tmp_path)` with pytest tmp_path fixture

---

## 8. Maintenance Guidelines

### When to Update Tests
1. **Bug Fixes**: Add regression test BEFORE fixing the bug
2. **New Features**: Write tests alongside implementation (TDD)
3. **Refactoring**: Tests should still pass; update if API changes
4. **Deprecations**: Mark tests with `pytest.mark.skip` and reason

### When to Rewrite Tests
1. Test is flaky despite fixes
2. Test duplicates coverage of other tests
3. Test tests implementation details instead of behavior
4. Test is too slow (>1 second for unit test)

### Identifying Flaky Tests
```bash
# Run tests 100 times to find flakiness
pytest --count=100 -x tests/integration/test_payment_api.py
```

### Test Performance Optimization
```bash
# Profile test execution time
pytest --durations=20

# Run only fast tests during development
pytest -m "not slow"
```

---

## 9. Resources & Further Learning

### Books
- **"Test Driven Development: By Example"** - Kent Beck
- **"Python Testing with pytest"** - Brian Okken
- **"Django for APIs"** - William S. Vincent

### Documentation
- [pytest-django](https://pytest-django.readthedocs.io/)
- [Factory Boy](https://factoryboy.readthedocs.io/)
- [Django Testing Tools](https://docs.djangoproject.com/en/5.0/topics/testing/)
- [REST Framework Testing](https://www.django-rest-framework.org/api-guide/testing/)

### Tools
- [Coverage.py](https://coverage.readthedocs.io/)
- [pytest plugins](https://docs.pytest.org/en/stable/reference/plugin_list.html)
- [Hypothesis](https://hypothesis.readthedocs.io/) for property-based testing

---

## 10. Quick Start Commands

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest shop/tests/unit/test_models.py

# Run tests matching pattern
pytest -k "payment"

# Run in parallel
pytest -n auto

# Run with verbose output
pytest -vv

# Run only failed tests from last run
pytest --lf

# Generate HTML coverage report
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

---

## Appendix: Test Metrics Dashboard

Track these metrics weekly:

| Metric | Target | Current | Trend |
|--------|--------|---------|-------|
| Line Coverage | 90% | TBD | ⬆️ |
| Branch Coverage | 85% | TBD | ⬆️ |
| Test Count | 500+ | TBD | ⬆️ |
| Test Duration | <2 min | TBD | ⬇️ |
| Flaky Tests | 0 | TBD | ⬇️ |
| Mutation Score | 80%+ | TBD | ⬆️ |

---

**Document Version**: 1.0
**Last Updated**: 2025-12-12
**Owner**: Engineering Team
**Review Cycle**: Quarterly
