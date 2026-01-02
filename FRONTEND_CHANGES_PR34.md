# Frontend Changes Required - PR #34: Standardized Error Response Format

**Date**: 2026-01-02
**PR**: https://github.com/Arianhf/derakht_backend/pull/83
**Risk Level**: HIGH - Breaking change for error handling
**Status**: Pending frontend update

---

## Overview

We have standardized the error response format across all API endpoints. This is a **breaking change** that requires frontend code updates.

## Changes Summary

All API error responses now return a consistent format, regardless of the error type or endpoint.

---

## New Error Response Format

### Standard Structure

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "User-friendly error message",
    "details": {}
  }
}
```

### Fields

- **`error.code`** (string): Machine-readable error code for programmatic handling
- **`error.message`** (string): User-friendly error message (currently in English, will be Persian in PR #35)
- **`error.details`** (object): Additional error context (e.g., field-level validation errors)

---

## Error Codes

| Code | HTTP Status | Meaning | Example Use Case |
|------|-------------|---------|------------------|
| `VALIDATION_ERROR` | 400 | Invalid input data | Missing required field, invalid format |
| `NOT_AUTHENTICATED` | 401 | Authentication required | Access without JWT token |
| `AUTHENTICATION_FAILED` | 401 | Invalid credentials | Wrong email/password |
| `PERMISSION_DENIED` | 403 | Insufficient permissions | Non-admin accessing admin endpoint |
| `NOT_FOUND` | 404 | Resource not found | Invalid product ID |
| `METHOD_NOT_ALLOWED` | 405 | HTTP method not allowed | POST to read-only endpoint |
| `PARSE_ERROR` | 400 | Request parsing failed | Malformed JSON |
| `THROTTLED` | 429 | Rate limit exceeded | Too many requests |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | Wrong content type | Sending XML instead of JSON |
| `INTERNAL_ERROR` | 500 | Server error | Unhandled exception |
| `UNKNOWN_ERROR` | varies | Unmapped error type | Edge case errors |

---

## Examples

### Example 1: Validation Error

**Request**: `POST /api/shop/cart/add_item/`
```json
{
  "product_id": "invalid-uuid"
}
```

**Old Response** (before PR #34):
```json
{
  "product_id": ["شناسه محصول معتبر نیست"],
  "quantity": ["این فیلد الزامی است"]
}
```

**New Response** (after PR #34):
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "شناسه محصول معتبر نیست",
    "details": {
      "product_id": ["شناسه محصول معتبر نیست"],
      "quantity": ["این فیلد الزامی است"]
    }
  }
}
```

### Example 2: Authentication Error

**Request**: `GET /api/shop/orders/` (without token)

**Old Response**:
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**New Response**:
```json
{
  "error": {
    "code": "NOT_AUTHENTICATED",
    "message": "Authentication credentials were not provided.",
    "details": {}
  }
}
```

### Example 3: Not Found Error

**Request**: `GET /api/shop/products/invalid-uuid/`

**Old Response**:
```json
{
  "detail": "Not found."
}
```

**New Response**:
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Not found.",
    "details": {}
  }
}
```

### Example 4: Login Failure

**Request**: `POST /api/users/login/`
```json
{
  "email": "user@example.com",
  "password": "wrongpassword"
}
```

**Old Response**:
```json
{
  "error": "Invalid credentials"
}
```

**New Response**:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid credentials",
    "details": {}
  }
}
```

---

## Frontend Implementation Guide

### 1. Update Axios Interceptor

Update your error interceptor to handle the new format:

```typescript
// Before
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail ||
                   error.response?.data?.error ||
                   'خطایی رخ داد';
    // Show error message
  }
);

// After
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    const errorData = error.response?.data?.error;
    const message = errorData?.message || 'خطایی رخ داد';
    const code = errorData?.code;
    const details = errorData?.details || {};

    // Handle based on error code
    if (code === 'NOT_AUTHENTICATED') {
      // Redirect to login
    } else if (code === 'VALIDATION_ERROR') {
      // Show validation errors
    }

    return Promise.reject(error);
  }
);
```

### 2. Update Form Validation

For forms, extract field-level errors from `details`:

```typescript
// Before
const errors = response.data;
setFieldError('email', errors.email?.[0]);

// After
const errorDetails = response.data?.error?.details || {};
setFieldError('email', errorDetails.email?.[0]);
```

### 3. Update Error Display Components

```typescript
// Before
interface ApiError {
  detail?: string;
  error?: string;
  [key: string]: any;
}

// After
interface ApiError {
  error: {
    code: string;
    message: string;
    details: Record<string, any>;
  };
}

// Usage
function ErrorDisplay({ error }: { error: ApiError }) {
  return (
    <div>
      <p>{error.error.message}</p>
      {Object.entries(error.error.details).map(([field, messages]) => (
        <p key={field}>{field}: {messages[0]}</p>
      ))}
    </div>
  );
}
```

### 4. Type Definitions

Add TypeScript types for the new format:

```typescript
export interface ApiErrorResponse {
  error: {
    code: ErrorCode;
    message: string;
    details: Record<string, string[]>;
  };
}

export type ErrorCode =
  | 'VALIDATION_ERROR'
  | 'NOT_AUTHENTICATED'
  | 'AUTHENTICATION_FAILED'
  | 'PERMISSION_DENIED'
  | 'NOT_FOUND'
  | 'METHOD_NOT_ALLOWED'
  | 'PARSE_ERROR'
  | 'THROTTLED'
  | 'UNSUPPORTED_MEDIA_TYPE'
  | 'INTERNAL_ERROR'
  | 'UNKNOWN_ERROR';
```

---

## Testing Checklist

Before deploying frontend changes, test these scenarios in staging:

- [ ] Login with invalid credentials
- [ ] Access protected endpoint without token
- [ ] Submit form with missing required fields
- [ ] Submit form with invalid data format
- [ ] Access non-existent resource (404)
- [ ] Add item to cart with invalid product ID
- [ ] Apply invalid promo code
- [ ] Request password reset for non-existent user
- [ ] Upload profile image with invalid file type
- [ ] Exceed rate limits (if applicable)

---

## Migration Timeline

1. **Backend Deploy to Staging**: PR #34 merged and deployed
2. **Frontend Updates**: Update error handling code
3. **Staging Testing**: Test all error scenarios
4. **Production Deploy**: Coordinate backend + frontend deployment

---

## Affected Endpoints

This change affects **ALL API endpoints**. Key areas:

### Authentication & Users
- `POST /api/users/login/`
- `POST /api/users/signup/`
- `PATCH /api/users/profile/`
- `POST /api/users/profile/image/`
- `POST /api/users/password-reset/`

### Shop & Cart
- `POST /api/shop/cart/add_item/`
- `POST /api/shop/cart/checkout/`
- `POST /api/shop/cart/shipping_estimate/`
- `POST /api/shop/orders/`
- `GET /api/shop/products/{id}/`

### Stories
- `POST /api/stories/collections/{id}/add_story/`
- `POST /api/stories/collections/{id}/remove_story/`
- All story creation and management endpoints

---

## Support & Questions

For questions or issues during frontend integration:
- Review PR: https://github.com/Arianhf/derakht_backend/pull/83
- Check backend code: `core/exceptions.py`
- Test in staging environment first

---

## Future Changes

**Note**: PR #35 will convert all error messages to Persian. The structure will remain the same, but the `message` field will be in Persian.
