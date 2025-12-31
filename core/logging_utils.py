"""
Logging utilities for Derrakht.ir platform.

Provides structured logging, performance tracking, and audit trail utilities.
"""

import json
import logging
import time
from functools import wraps
from typing import Any, Dict, Optional, Callable
from contextlib import contextmanager
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging in production.

    Outputs log records as JSON for easy parsing by log aggregation tools.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "extra_data"):
            log_data["extra_data"] = record.extra_data

        return json.dumps(log_data, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__ from the calling module)

    Returns:
        Logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Story created", extra={"story_id": story.id})
    """
    return logging.getLogger(name)


def log_performance(operation: str, logger_name: Optional[str] = None):
    """
    Decorator to log function execution time.

    Args:
        operation: Description of the operation being performed
        logger_name: Optional logger name (defaults to 'performance')

    Example:
        @log_performance("story_generation")
        def create_story(template_id):
            # ... story creation logic
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name or "performance")
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                logger.info(
                    f"{operation} completed in {duration_ms:.2f}ms",
                    extra={
                        "operation": operation,
                        "function": func.__name__,
                        "duration_ms": duration_ms,
                        "status": "success",
                    },
                )

                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"{operation} failed after {duration_ms:.2f}ms: {str(e)}",
                    extra={
                        "operation": operation,
                        "function": func.__name__,
                        "duration_ms": duration_ms,
                        "status": "error",
                        "error": str(e),
                    },
                    exc_info=True,
                )
                raise

        return wrapper
    return decorator


@contextmanager
def log_operation(
    operation: str,
    logger: logging.Logger,
    level: int = logging.INFO,
    extra_data: Optional[Dict[str, Any]] = None,
):
    """
    Context manager for logging an operation with timing.

    Args:
        operation: Description of the operation
        logger: Logger instance to use
        level: Log level (default: INFO)
        extra_data: Additional data to include in log

    Example:
        logger = get_logger(__name__)
        with log_operation("story_generation", logger, extra_data={"template_id": 123}):
            # ... perform story generation
            pass
    """
    start_time = time.time()
    extra = extra_data or {}

    logger.log(level, f"{operation} started", extra={"extra_data": extra})

    try:
        yield
        duration_ms = (time.time() - start_time) * 1000
        logger.log(
            level,
            f"{operation} completed in {duration_ms:.2f}ms",
            extra={
                "duration_ms": duration_ms,
                "extra_data": extra,
                "status": "success",
            },
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"{operation} failed after {duration_ms:.2f}ms: {str(e)}",
            extra={
                "duration_ms": duration_ms,
                "extra_data": extra,
                "status": "error",
                "error": str(e),
            },
            exc_info=True,
        )
        raise


def log_user_action(
    logger: logging.Logger,
    action: str,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
):
    """
    Log a user action for audit trail.

    Args:
        logger: Logger instance (typically 'audit' logger)
        action: Description of the action
        user_id: User ID performing the action
        user_email: User email
        extra_data: Additional context data

    Example:
        log_user_action(
            audit_logger,
            "story_created",
            user_id=request.user.id,
            user_email=request.user.email,
            extra_data={"story_id": story.id, "template_id": template.id}
        )
    """
    log_data = {
        "action": action,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if user_id:
        log_data["user_id"] = user_id
    if user_email:
        log_data["user_email"] = user_email
    if extra_data:
        log_data.update(extra_data)

    logger.info(
        f"User action: {action}",
        extra={"extra_data": log_data},
    )


def log_analytics_event(
    event_name: str,
    event_category: str,
    user_id: Optional[int] = None,
    properties: Optional[Dict[str, Any]] = None,
):
    """
    Log an analytics event for user behavior tracking.

    Args:
        event_name: Name of the event (e.g., "story_completed")
        event_category: Category (e.g., "stories", "shop", "user")
        user_id: Optional user ID
        properties: Event properties

    Example:
        log_analytics_event(
            "story_completed",
            "stories",
            user_id=request.user.id,
            properties={
                "story_id": story.id,
                "parts_count": story.parts.count(),
                "activity_type": story.activity_type,
            }
        )
    """
    logger = logging.getLogger("analytics")

    event_data = {
        "event_name": event_name,
        "event_category": event_category,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if user_id:
        event_data["user_id"] = user_id
    if properties:
        event_data["properties"] = properties

    logger.info(
        f"Analytics: {event_category}.{event_name}",
        extra={"extra_data": event_data},
    )


def log_api_error(
    logger: logging.Logger,
    error: Exception,
    request_path: str,
    request_method: str,
    user_id: Optional[int] = None,
    request_data: Optional[Dict[str, Any]] = None,
):
    """
    Log an API error with full context.

    Args:
        logger: Logger instance
        error: Exception that occurred
        request_path: API endpoint path
        request_method: HTTP method
        user_id: User ID if authenticated
        request_data: Request data (sanitized)

    Example:
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
    """
    error_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "request_path": request_path,
        "request_method": request_method,
    }

    if user_id:
        error_data["user_id"] = user_id
    if request_data:
        # Sanitize sensitive data
        sanitized_data = _sanitize_data(request_data)
        error_data["request_data"] = sanitized_data

    logger.error(
        f"API Error: {request_method} {request_path} - {type(error).__name__}: {str(error)}",
        extra={"extra_data": error_data},
        exc_info=True,
    )


def log_security_event(
    event_type: str,
    severity: str,
    description: str,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
):
    """
    Log a security-related event.

    Args:
        event_type: Type of security event (e.g., "auth_failure", "suspicious_activity")
        severity: Severity level ("low", "medium", "high", "critical")
        description: Event description
        user_id: User ID if applicable
        ip_address: IP address
        extra_data: Additional context

    Example:
        log_security_event(
            "auth_failure",
            "medium",
            "Failed login attempt with invalid credentials",
            user_id=None,
            ip_address=get_client_ip(request),
            extra_data={"email": email, "attempt_count": 3}
        )
    """
    logger = logging.getLogger("django.security")

    security_data = {
        "event_type": event_type,
        "severity": severity,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if user_id:
        security_data["user_id"] = user_id
    if ip_address:
        security_data["ip_address"] = ip_address
    if extra_data:
        security_data.update(extra_data)

    # Map severity to log level
    level_map = {
        "low": logging.INFO,
        "medium": logging.WARNING,
        "high": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    level = level_map.get(severity, logging.WARNING)

    logger.log(
        level,
        f"Security event: {event_type} - {description}",
        extra={"extra_data": security_data},
    )


def _sanitize_data(data: Any) -> Any:
    """
    Sanitize sensitive data from logging.

    Removes passwords, tokens, and other sensitive fields.
    """
    if not isinstance(data, dict):
        return data

    sensitive_keys = {
        "password",
        "password1",
        "password2",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "api_key",
        "credit_card",
        "cvv",
        "ssn",
    }

    sanitized = {}
    for key, value in data.items():
        if key.lower() in sensitive_keys:
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_data(value)
        else:
            sanitized[key] = value

    return sanitized


def get_client_ip(request) -> str:
    """
    Get client IP address from request.

    Args:
        request: Django request object

    Returns:
        IP address string
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "unknown")
    return ip


def sanitize_payment_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove sensitive payment data from logs.

    Args:
        params: Payment parameters dictionary

    Returns:
        Sanitized dictionary with sensitive fields redacted

    Example:
        safe_params = sanitize_payment_params(request.GET.dict())
        logger.info("Payment callback", extra={"extra_data": {"params": safe_params}})
    """
    safe_params = params.copy()
    sensitive_keys = ['card_number', 'cvv', 'password', 'token', 'CardPan', 'cvv2']
    for key in sensitive_keys:
        if key in safe_params:
            safe_params[key] = '***REDACTED***'
    return safe_params


def hash_email(email: str) -> str:
    """
    Hash email for privacy-preserving logs.

    Args:
        email: Email address to hash

    Returns:
        First 16 characters of SHA256 hash of the email

    Example:
        logger.info("Password reset", extra={"email_hash": hash_email(email)})
    """
    import hashlib
    return hashlib.sha256(email.encode()).hexdigest()[:16]
