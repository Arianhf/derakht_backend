"""
Logging middleware for Derrakht.ir platform.

Provides request/response logging, performance tracking, and user context.
"""

import logging
import time
import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from .logging_utils import get_client_ip, _sanitize_data


logger = logging.getLogger("django.request")
performance_logger = logging.getLogger("performance")
analytics_logger = logging.getLogger("analytics")


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware for logging all HTTP requests and responses.

    Logs:
    - Request method, path, query parameters
    - User information (if authenticated)
    - Response status code
    - Request duration
    - Client IP address
    """

    def process_request(self, request: HttpRequest):
        """Process incoming request."""
        # Generate unique request ID for tracing
        request.request_id = str(uuid.uuid4())
        request.start_time = time.time()

        # Get client IP
        request.client_ip = get_client_ip(request)

        # Log request
        logger.info(
            f"Request started: {request.method} {request.path}",
            extra={
                "request_id": request.request_id,
                "method": request.method,
                "path": request.path,
                "query_params": dict(request.GET),
                "user_id": request.user.id if request.user.is_authenticated else None,
                "user_email": request.user.email if request.user.is_authenticated else None,
                "ip_address": request.client_ip,
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            },
        )

    def process_response(self, request: HttpRequest, response: HttpResponse):
        """Process outgoing response."""
        if hasattr(request, "start_time"):
            duration_ms = (time.time() - request.start_time) * 1000

            # Determine log level based on status code
            if response.status_code >= 500:
                log_level = logging.ERROR
            elif response.status_code >= 400:
                log_level = logging.WARNING
            else:
                log_level = logging.INFO

            # Log response
            logger.log(
                log_level,
                f"Request completed: {request.method} {request.path} - {response.status_code} in {duration_ms:.2f}ms",
                extra={
                    "request_id": getattr(request, "request_id", "unknown"),
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "user_id": request.user.id if request.user.is_authenticated else None,
                    "ip_address": getattr(request, "client_ip", "unknown"),
                },
            )

            # Log performance for slow requests (>1000ms)
            if duration_ms > 1000:
                performance_logger.warning(
                    f"Slow request detected: {request.method} {request.path} took {duration_ms:.2f}ms",
                    extra={
                        "request_id": getattr(request, "request_id", "unknown"),
                        "method": request.method,
                        "path": request.path,
                        "duration_ms": duration_ms,
                        "threshold": "1000ms",
                    },
                )

        return response

    def process_exception(self, request: HttpRequest, exception: Exception):
        """Process exception that occurred during request processing."""
        if hasattr(request, "start_time"):
            duration_ms = (time.time() - request.start_time) * 1000

            logger.error(
                f"Request failed: {request.method} {request.path} - {type(exception).__name__}: {str(exception)}",
                extra={
                    "request_id": getattr(request, "request_id", "unknown"),
                    "method": request.method,
                    "path": request.path,
                    "duration_ms": duration_ms,
                    "exception_type": type(exception).__name__,
                    "exception_message": str(exception),
                    "user_id": request.user.id if request.user.is_authenticated else None,
                    "ip_address": getattr(request, "client_ip", "unknown"),
                },
                exc_info=True,
            )


class UserContextMiddleware(MiddlewareMixin):
    """
    Middleware to add user context to all log records.

    Adds user_id and request_id to log records for better traceability.
    """

    def process_request(self, request: HttpRequest):
        """Add user context to logging."""
        # Store user info in thread-local storage for use in loggers
        if request.user.is_authenticated:
            # Add to logging context (this can be used by custom handlers)
            request.log_context = {
                "user_id": request.user.id,
                "user_email": request.user.email,
                "request_id": getattr(request, "request_id", None),
            }


class AnalyticsMiddleware(MiddlewareMixin):
    """
    Middleware for tracking user analytics and behavior.

    Tracks:
    - Page views
    - Feature usage
    - User journeys
    """

    # Paths to exclude from analytics
    EXCLUDE_PATHS = [
        "/admin/",
        "/content_admin/",
        "/static/",
        "/media/",
        "/favicon.ico",
    ]

    def process_response(self, request: HttpRequest, response: HttpResponse):
        """Track analytics events."""
        # Skip excluded paths
        if any(request.path.startswith(path) for path in self.EXCLUDE_PATHS):
            return response

        # Skip non-successful responses
        if response.status_code >= 400:
            return response

        # Track API usage
        if request.path.startswith("/api/"):
            self._track_api_usage(request, response)

        return response

    def _track_api_usage(self, request: HttpRequest, response: HttpResponse):
        """Track API endpoint usage."""
        # Extract API category from path
        path_parts = request.path.strip("/").split("/")
        if len(path_parts) >= 2:
            api_category = path_parts[1]  # e.g., 'stories', 'shop', 'users'

            analytics_logger.info(
                f"API usage: {api_category} - {request.method} {request.path}",
                extra={
                    "extra_data": {
                        "event_name": "api_request",
                        "api_category": api_category,
                        "method": request.method,
                        "path": request.path,
                        "status_code": response.status_code,
                        "user_id": request.user.id if request.user.is_authenticated else None,
                        "is_authenticated": request.user.is_authenticated,
                        "duration_ms": (time.time() - request.start_time) * 1000
                        if hasattr(request, "start_time")
                        else None,
                    }
                },
            )


class DatabaseQueryLoggingMiddleware(MiddlewareMixin):
    """
    Middleware for logging database query performance.

    Logs queries that exceed a threshold for optimization.
    """

    # Query count threshold for logging
    QUERY_COUNT_THRESHOLD = 50

    # Total query time threshold (ms)
    QUERY_TIME_THRESHOLD_MS = 500

    def process_request(self, request: HttpRequest):
        """Reset query tracking."""
        from django.db import reset_queries
        reset_queries()

    def process_response(self, request: HttpRequest, response: HttpResponse):
        """Log database query statistics."""
        from django.conf import settings
        from django.db import connection

        # Only log in DEBUG mode or if explicitly enabled
        if not settings.DEBUG:
            return response

        # Get query statistics
        queries = connection.queries
        query_count = len(queries)
        total_time = sum(float(q.get("time", 0)) for q in queries)
        total_time_ms = total_time * 1000

        # Log if thresholds exceeded
        if query_count > self.QUERY_COUNT_THRESHOLD or total_time_ms > self.QUERY_TIME_THRESHOLD_MS:
            performance_logger.warning(
                f"High database usage: {request.method} {request.path} - {query_count} queries in {total_time_ms:.2f}ms",
                extra={
                    "request_id": getattr(request, "request_id", "unknown"),
                    "method": request.method,
                    "path": request.path,
                    "query_count": query_count,
                    "total_query_time_ms": total_time_ms,
                    "query_count_threshold": self.QUERY_COUNT_THRESHOLD,
                    "time_threshold_ms": self.QUERY_TIME_THRESHOLD_MS,
                },
            )

            # Log slowest queries
            if queries:
                slowest_queries = sorted(queries, key=lambda q: float(q.get("time", 0)), reverse=True)[:5]
                for i, query in enumerate(slowest_queries, 1):
                    performance_logger.debug(
                        f"Slow query #{i}: {query['time']}s - {query['sql'][:200]}",
                        extra={
                            "query_time": query["time"],
                            "query_sql": query["sql"][:500],
                        },
                    )

        return response
