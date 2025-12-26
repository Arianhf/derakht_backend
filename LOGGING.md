# Logging System Documentation - Derrakht.ir

## Overview

The Derrakht.ir platform implements a comprehensive, production-ready logging system designed for:

1. **Debugging & Development**: Track request flow, data transformations, and edge cases
2. **Production Monitoring**: Alert on errors, performance issues, and suspicious activity
3. **User Analytics**: Non-intrusive tracking of feature usage and user journeys
4. **Performance Profiling**: Identify bottlenecks in PDF generation, image processing, and database queries
5. **Compliance & Auditing**: Track user content creation and data modifications

## Architecture

### Log Files

All logs are stored in the `logs/` directory (excluded from git):

- `derakht.log` - General application logs (10MB, 5 backups)
- `errors.log` - Error-level logs only (10MB, 10 backups)
- `security.log` - Security-related events (10MB, 10 backups)
- `performance.log` - Performance metrics and slow queries (10MB, 5 backups)
- `audit.log` - Audit trail for critical operations (10MB, 20 backups)
- `analytics.log` - User analytics events in JSON format (10MB, 10 backups)

### Log Levels

Configure the log level via environment variable:

```bash
export DJANGO_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

Default: `INFO` in production, `DEBUG` in development (when `DEBUG=1`)

### Loggers

#### Application Loggers

- `stories` - Stories app general logs
- `stories.generation` - Story creation and template instantiation
- `stories.images` - Image uploads and processing
- `shop` - Shop app general logs
- `shop.payments` - Payment processing and transactions
- `shop.orders` - Order management and status changes
- `users` - Users app general logs
- `users.auth` - Authentication and authorization
- `blog` - Blog/CMS operations
- `core` - Core features and utilities

#### System Loggers

- `performance` - Performance metrics
- `analytics` - User behavior analytics (JSON format)
- `audit` - Audit trail for compliance
- `django.security` - Django security events
- `django.request` - HTTP request/response logs

## Usage

### Basic Logging

```python
from core.logging_utils import get_logger

logger = get_logger(__name__)

# Standard logging
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)
logger.critical("Critical issue")

# With extra context
logger.info(
    "Story created",
    extra={
        "extra_data": {
            "story_id": story.id,
            "user_id": user.id,
            "template_id": template.id,
        }
    },
)
```

### Performance Tracking

#### Using Decorator

```python
from core.logging_utils import log_performance

@log_performance("story_generation")
def create_story_from_template(template_id, user):
    # ... implementation
    pass
```

#### Using Context Manager

```python
from core.logging_utils import log_operation, get_logger

logger = get_logger(__name__)

with log_operation("pdf_generation", logger, extra_data={"story_id": 123}):
    # ... generate PDF
    pass
```

### Audit Logging

Track critical user actions for compliance:

```python
from core.logging_utils import log_user_action, get_logger

audit_logger = get_logger("audit")

log_user_action(
    audit_logger,
    "story_completed",
    user_id=request.user.id,
    user_email=request.user.email,
    extra_data={
        "story_id": story.id,
        "story_title": story.title,
        "activity_type": story.activity_type,
    },
)
```

### Analytics Events

Track user behavior and feature usage:

```python
from core.logging_utils import log_analytics_event

log_analytics_event(
    "story_completed",
    "stories",
    user_id=request.user.id,
    properties={
        "story_id": story.id,
        "activity_type": story.activity_type,
        "parts_count": story.parts.count(),
    },
)
```

### Security Events

Log security-related events:

```python
from core.logging_utils import log_security_event, get_client_ip

log_security_event(
    "auth_failure",
    "medium",  # low, medium, high, critical
    f"Failed login attempt for email: {email}",
    ip_address=get_client_ip(request),
    extra_data={"email": email},
)
```

### API Error Logging

```python
from core.logging_utils import log_api_error, get_logger

logger = get_logger(__name__)

try:
    # ... API logic
except Exception as e:
    log_api_error(
        logger,
        e,
        request.path,
        request.method,
        user_id=request.user.id if request.user.is_authenticated else None,
        request_data=request.data,
    )
    raise
```

## Middleware

The logging system includes four middleware components (already configured):

### 1. RequestLoggingMiddleware

Logs all HTTP requests and responses with:
- Request method, path, query parameters
- User information (if authenticated)
- Response status code and duration
- Client IP address and user agent

### 2. UserContextMiddleware

Adds user context to all log records for better traceability.

### 3. AnalyticsMiddleware

Tracks API endpoint usage and user journeys. Automatically logs:
- API endpoint calls
- Response status codes
- Request durations
- Authenticated vs anonymous usage

### 4. DatabaseQueryLoggingMiddleware

Monitors database performance (DEBUG mode only):
- Logs when query count exceeds 50
- Logs when total query time exceeds 500ms
- Shows slowest queries for optimization

## Logged Events by App

### Stories App

**Logged Events:**
- Story creation from template (`story_started`)
- Canvas data updates (`story_part_updated`)
- Story completion (`story_completed`)
- Cover image uploads (`story_cover_uploaded`)
- Illustration uploads (`story_part_illustration_uploaded`)
- Story part resets

**Analytics Events:**
- `story_started` - User creates new story
- `story_completed` - User completes story
- `illustration_uploaded` - User uploads illustration

### Shop App

**Logged Events:**
- Payment request initiation (`payment_requested`)
- Payment gateway callbacks
- Payment verification (success/failure)
- Payment completion (`payment_completed`)
- Invoice creation (`invoice_created`)
- Order status changes (`order_status_changed`)
- Order item modifications

**Security Events:**
- Unauthorized payment access attempts
- Payment verification failures

### Users App

**Logged Events:**
- User registration (`user_registered`)
- User login (`user_login`)
- Profile updates (`profile_updated`)
- Profile image uploads/deletions

**Security Events:**
- Failed login attempts (`auth_failure`)
- Invalid credentials

## Log Format

### Development Format (Verbose)

```
[INFO] 2025-12-26 10:30:45 stories.generation views.start_story:122 | Story created from template: 42
```

Format: `[LEVEL] TIMESTAMP LOGGER MODULE.FUNCTION:LINE | MESSAGE`

### Production Format (Simple)

```
[INFO] 2025-12-26 10:30:45 stories.generation | Story created from template: 42
```

### JSON Format (Analytics)

```json
{
  "timestamp": "2025-12-26T10:30:45.123456",
  "level": "INFO",
  "logger": "analytics",
  "message": "Analytics: stories.story_started",
  "extra_data": {
    "event_name": "story_started",
    "event_category": "stories",
    "user_id": 123,
    "properties": {
      "template_id": 42,
      "activity_type": "WRITE_FOR_DRAWING",
      "parts_count": 5
    }
  }
}
```

## Best Practices

### 1. Use Appropriate Log Levels

- **DEBUG**: Detailed diagnostic information (development only)
- **INFO**: General informational messages (normal operations)
- **WARNING**: Warning messages (potential issues)
- **ERROR**: Error messages (operation failed but app continues)
- **CRITICAL**: Critical issues (app may not function)

### 2. Include Context

Always include relevant IDs and context:

```python
logger.info(
    f"Payment verified: {payment.id}",
    extra={
        "extra_data": {
            "payment_id": str(payment.id),
            "order_id": str(order.id),
            "amount": float(payment.amount),
            "gateway": gateway,
        }
    },
)
```

### 3. Sanitize Sensitive Data

The logging utilities automatically sanitize passwords, tokens, and credit card data. Additional sensitive fields can be added to `_sanitize_data()` in `core/logging_utils.py`.

### 4. Use Structured Logging

For analytics and audit logs, use the `extra_data` field for machine-readable structured data.

### 5. Log User Actions

For compliance, always log:
- Data creation (stories, orders, invoices)
- Data modifications (updates, deletions)
- Authentication events (login, logout, failures)
- Payment transactions

## Monitoring & Alerts

### Performance Alerts

Slow requests (>1000ms) are automatically logged to `performance.log`:

```
[WARNING] Slow request detected: POST /api/stories/templates/42/start_story/ took 1523.45ms
```

### Database Alerts

High database usage is logged when:
- Query count > 50
- Total query time > 500ms

### Security Alerts

Failed authentication attempts are logged to `security.log` with severity levels.

## Log Rotation

All log files use `RotatingFileHandler`:
- Maximum file size: 10MB
- Backup count varies by log type (5-20 backups)
- Old logs are automatically rotated

## Production Deployment

### Environment Variables

```bash
# Set log level
export DJANGO_LOG_LEVEL=INFO

# Ensure DEBUG is disabled
export DJANGO_DEBUG=0
```

### Log Aggregation

For production, consider integrating with log aggregation services:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Graylog**
- **Splunk**
- **Datadog**
- **Sentry** (for error tracking)

The JSON formatter in `analytics.log` is designed for easy ingestion into log aggregation tools.

### Log Storage

In production:
1. Ensure `/home/user/derakht_backend/logs/` has appropriate permissions
2. Consider using a dedicated log volume
3. Set up log backup and archival
4. Monitor disk space usage

## Troubleshooting

### Logs Not Appearing

1. Check `DEBUG` setting matches expected log level
2. Verify `DJANGO_LOG_LEVEL` environment variable
3. Check file permissions on `logs/` directory
4. Ensure middleware is properly configured in `settings.py`

### Performance Issues

1. Review `performance.log` for slow requests
2. Check `DATABASE` logs for N+1 queries
3. Use Django Debug Toolbar in development
4. Review `analytics.log` for usage patterns

### Security Investigations

1. Review `security.log` for failed auth attempts
2. Check `audit.log` for user actions timeline
3. Filter by IP address for suspicious activity
4. Cross-reference with `analytics.log` for behavior patterns

## Examples

### Complete Story Creation Example

```python
from core.logging_utils import (
    get_logger,
    log_user_action,
    log_analytics_event,
    log_operation,
)

logger = get_logger("stories.generation")
audit_logger = get_logger("audit")

with log_operation("story_generation", logger, extra_data={"template_id": template.id}):
    story = Story.objects.create(...)

    logger.info(
        f"Story created: {story.id}",
        extra={
            "extra_data": {
                "story_id": story.id,
                "template_id": template.id,
                "user_id": user.id,
            }
        },
    )

    log_user_action(
        audit_logger,
        "story_started",
        user_id=user.id,
        user_email=user.email,
        extra_data={"story_id": story.id},
    )

    log_analytics_event(
        "story_started",
        "stories",
        user_id=user.id,
        properties={"template_id": template.id},
    )
```

### Payment Processing Example

```python
from core.logging_utils import get_logger, log_security_event

logger = get_logger("shop.payments")

logger.info(
    f"Payment request initiated for order {order.id}",
    extra={
        "extra_data": {
            "order_id": str(order.id),
            "amount": float(order.total_amount),
            "gateway": gateway,
        }
    },
)

try:
    result = PaymentService.request_payment(order, gateway)

    if result["success"]:
        logger.info(f"Payment request successful: {result['payment_id']}")
    else:
        logger.error(f"Payment request failed: {result['error_message']}")

except Exception as e:
    logger.error(f"Payment processing error: {str(e)}", exc_info=True)
    raise
```

## Summary

The logging system provides comprehensive visibility into:
- ✅ All HTTP requests and responses
- ✅ User authentication and authorization
- ✅ Story creation and modification
- ✅ Payment processing and verification
- ✅ Order management and invoicing
- ✅ Image uploads and processing
- ✅ Performance bottlenecks
- ✅ Security events and failures
- ✅ User behavior analytics
- ✅ Audit trail for compliance

For questions or issues, refer to the Django logging documentation: https://docs.djangoproject.com/en/5.0/topics/logging/
