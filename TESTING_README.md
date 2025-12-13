# Testing Guide for Derakht Backend

## Quick Start

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage report
pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Running Tests](#running-tests)
4. [Test Organization](#test-organization)
5. [Writing Tests](#writing-tests)
6. [Coverage Reports](#coverage-reports)
7. [Continuous Integration](#continuous-integration)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python 3.12+**
- **PostgreSQL** (for test database)
- **Virtual environment** (recommended)

## Installation

### 1. Set Up Test Environment

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### 2. Configure Test Database

Create a test database in PostgreSQL:

```sql
CREATE DATABASE test_derakht;
GRANT ALL PRIVILEGES ON DATABASE test_derakht TO your_user;
```

### 3. Set Environment Variables

Create a `.env.test` file:

```env
TEST_DB_NAME=test_derakht
TEST_DB_USER=postgres
TEST_DB_PASSWORD=your_password
TEST_DB_HOST=localhost
TEST_DB_PORT=5432

ZARINPAL_MERCHANT_ID=test-merchant-id
ZARINPAL_SANDBOX=True
```

---

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest shop/tests/unit/test_order_management.py

# Run specific test class
pytest shop/tests/unit/test_order_management.py::TestOrderStatusTransition

# Run specific test method
pytest shop/tests/unit/test_order_management.py::TestOrderStatusTransition::test_valid_transitions_from_cart_to_pending

# Run tests matching a keyword
pytest -k "payment"

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only payment-related tests
pytest -m payment
```

### Advanced Options

```bash
# Run tests in parallel (faster)
pytest -n auto

# Stop on first failure
pytest -x

# Run only failed tests from last run
pytest --lf

# Run failed tests first, then all others
pytest --ff

# Show slowest 10 tests
pytest --durations=10

# Run tests with coverage
pytest --cov=. --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=. --cov-report=html

# Exclude slow tests
pytest -m "not slow"

# Run slow tests only
pytest -m slow --runslow
```

### Test Selection by App

```bash
# Shop app tests
pytest shop/tests/

# Users app tests
pytest users/tests/

# Stories app tests
pytest stories/tests/

# Only unit tests for shop
pytest shop/tests/unit/

# Only integration tests for users
pytest users/tests/integration/
```

---

## Test Organization

### Directory Structure

```
app_name/
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # App-specific fixtures
│   ├── factories.py         # Factory Boy factories
│   │
│   ├── unit/                # Unit tests (60% of tests)
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_serializers.py
│   │   └── test_services.py
│   │
│   ├── integration/         # Integration tests (30% of tests)
│   │   ├── __init__.py
│   │   ├── test_api.py
│   │   └── test_permissions.py
│   │
│   └── e2e/                 # End-to-end tests (10% of tests)
│       ├── __init__.py
│       └── test_user_flows.py
```

### Test Categories

#### Unit Tests (`-m unit`)
- Test individual functions, methods, and classes
- No database queries (or minimal)
- Fast execution (< 100ms per test)
- High coverage of business logic

**Examples:**
- Model methods
- Serializer validation
- Utility functions
- State machine logic

#### Integration Tests (`-m integration`)
- Test API endpoints
- Database interactions
- Authentication/permissions
- External service mocking

**Examples:**
- API endpoint behavior
- Database constraints
- Permission checks
- Payment gateway integration (mocked)

#### End-to-End Tests (`-m e2e`)
- Complete user workflows
- Multiple components working together
- Slower execution

**Examples:**
- Complete checkout flow
- User registration → verification → login → purchase
- Story creation from template to completion

---

## Writing Tests

### Test Structure (AAA Pattern)

```python
def test_add_product_to_cart(authenticated_client, product):
    # ARRANGE - Set up test data
    quantity = 2

    # ACT - Perform the action
    url = reverse("cart-add-item")
    response = authenticated_client.post(url, {
        "product_id": product.id,
        "quantity": quantity
    })

    # ASSERT - Verify outcomes
    assert response.status_code == 200
    assert CartItem.objects.filter(product=product).exists()
    cart_item = CartItem.objects.get(product=product)
    assert cart_item.quantity == quantity
```

### Using Factories

```python
from shop.tests.factories import ProductFactory, OrderFactory

def test_order_total():
    # Create product with specific price
    product = ProductFactory(price=Decimal("99.99"), stock=10)

    # Create order with 3 items
    order = OrderFactory(items=3)

    # Or use helper functions
    from shop.tests.factories import create_order_with_items
    order = create_order_with_items(item_count=5, status="PENDING")
```

### Parametrized Tests

```python
import pytest

@pytest.mark.parametrize("initial_status,target_status,should_succeed", [
    ("PENDING", "PROCESSING", True),
    ("PENDING", "DELIVERED", False),
    ("DELIVERED", "PENDING", False),
])
def test_order_transitions(order_factory, initial_status, target_status, should_succeed):
    order = order_factory(status=initial_status)

    if should_succeed:
        order.transition_to(target_status)
        assert order.status == target_status
    else:
        with pytest.raises(ValidationError):
            order.transition_to(target_status)
```

### Mocking External Services

```python
import responses

@responses.activate
def test_zarinpal_payment(order, mock_zarinpal_success):
    # Mock is set up via fixture
    mock_zarinpal_success()

    # Make request that calls Zarinpal
    service = PaymentService()
    result = service.request_payment(order, "zarinpal")

    assert result["authority"] is not None
```

### Testing Email Sending

```python
from django.core import mail

def test_password_reset_email(api_client, user, mock_email_backend):
    url = reverse("request-password-reset")
    response = api_client.post(url, {"email": user.email})

    assert len(mail.outbox) == 1
    assert user.email in mail.outbox[0].to
    assert "password" in mail.outbox[0].subject.lower()
```

### Testing File Uploads

```python
from django.core.files.uploadedfile import SimpleUploadedFile

def test_profile_image_upload(authenticated_client):
    image = SimpleUploadedFile(
        "profile.jpg",
        b"fake_image_content",
        content_type="image/jpeg"
    )

    url = reverse("user-profile-image")
    response = authenticated_client.post(url, {"profile_image": image})

    assert response.status_code == 200
```

---

## Coverage Reports

### Generating Coverage

```bash
# Terminal report
pytest --cov=. --cov-report=term-missing

# HTML report
pytest --cov=. --cov-report=html
open htmlcov/index.html

# XML report (for CI/CD)
pytest --cov=. --cov-report=xml

# All three
pytest --cov=. --cov-report=term-missing --cov-report=html --cov-report=xml
```

### Coverage Targets

| Component | Target | Priority |
|-----------|--------|----------|
| Payment Processing | 95%+ | P0 |
| Order State Machine | 95%+ | P0 |
| Authentication | 90%+ | P0 |
| Cart Operations | 90%+ | P1 |
| Product API | 85%+ | P1 |
| Story Creation | 80%+ | P1 |
| Models | 85%+ | P1 |
| Serializers | 80%+ | P2 |
| Views | 75%+ | P2 |

### Checking Coverage Thresholds

```bash
# Fail if coverage below 80%
pytest --cov=. --cov-fail-under=80

# Check specific app coverage
pytest --cov=shop --cov-fail-under=85 shop/tests/
```

---

## Continuous Integration

### GitHub Actions

The project includes a `.github/workflows/test.yml` file that:

- Runs on every push and pull request
- Sets up PostgreSQL service
- Installs dependencies
- Runs full test suite with coverage
- Uploads coverage to Codecov
- Fails if coverage drops below threshold

### Running Tests Locally Like CI

```bash
# Simulate CI environment
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test_derakht
pytest --cov=. --cov-report=xml --cov-fail-under=80
```

### Pre-commit Hooks

Install pre-commit hooks to run tests before commits:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

**Problem:** `django.db.utils.OperationalError: could not connect to server`

**Solution:**
```bash
# Verify PostgreSQL is running
pg_isready

# Check connection settings
echo $DATABASE_URL

# Create test database if missing
createdb test_derakht
```

#### 2. Import Errors

**Problem:** `ModuleNotFoundError: No module named 'shop'`

**Solution:**
```bash
# Ensure pytest is run from project root
cd /path/to/derakht_backend

# Check PYTHONPATH
export PYTHONPATH=.
```

#### 3. Test Database Not Isolated

**Problem:** Tests fail intermittently due to shared state

**Solution:**
```bash
# Use --reuse-db flag carefully
pytest --create-db  # Force recreate database

# Or drop and recreate manually
dropdb test_derakht
createdb test_derakht
```

#### 4. Slow Tests

**Problem:** Test suite takes too long

**Solution:**
```bash
# Run in parallel
pytest -n auto

# Profile slow tests
pytest --durations=20

# Skip slow tests during development
pytest -m "not slow"
```

#### 5. Mocking Issues

**Problem:** `ConnectionError` when running tests (real API calls)

**Solution:**
- Ensure `@responses.activate` decorator is used
- Check mock fixtures are properly configured
- Verify test uses mocked client/service

#### 6. Factory Errors

**Problem:** `IntegrityError` or circular dependencies in factories

**Solution:**
```python
# Use SubFactory instead of direct foreign key
class OrderFactory(DjangoModelFactory):
    user = factory.SubFactory(UserFactory)  # ✅ Correct

    # NOT:
    # user = UserFactory()  # ❌ Wrong

# For optional relationships
class OrderFactory(DjangoModelFactory):
    promo_code = None  # Default to None
```

---

## Best Practices

### 1. Test Independence
- Each test should run independently
- Don't rely on test execution order
- Clean up after yourself (fixtures handle this)

### 2. Clear Test Names
```python
# ✅ Good
def test_user_cannot_view_other_users_orders()

# ❌ Bad
def test_orders()
```

### 3. One Assertion Per Concept
```python
# ✅ Good
def test_order_total_calculation():
    order = create_order_with_items(item_count=3)
    expected_total = sum(item.total_price for item in order.items.all())
    assert order.total_amount == expected_total

# ❌ Bad
def test_order():
    order = create_order_with_items()
    assert order.total_amount > 0
    assert order.status == "PENDING"
    assert order.user is not None
    # Too many unrelated assertions
```

### 4. Use Fixtures for Setup
```python
# ✅ Good
def test_payment_verification(payment_flow):
    order, payment, transaction = payment_flow
    # Test logic

# ❌ Bad
def test_payment_verification():
    user = UserFactory()
    order = OrderFactory(user=user)
    payment = PaymentFactory(order=order)
    # Repetitive setup in every test
```

### 5. Test Edge Cases
- Boundary values
- Empty inputs
- Null values
- Invalid data
- Concurrent access
- Error conditions

---

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Factory Boy Documentation](https://factoryboy.readthedocs.io/)
- [Django Testing Tools](https://docs.djangoproject.com/en/stable/topics/testing/)
- [REST Framework Testing](https://www.django-rest-framework.org/api-guide/testing/)

---

## Support

For questions or issues with tests:

1. Check this README
2. Review `TESTING_STRATEGY.md` for detailed strategy
3. Look at existing test examples in the codebase
4. Ask the team in #engineering channel

---

**Last Updated:** 2025-12-12
**Maintained By:** Engineering Team
