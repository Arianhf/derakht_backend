# Security Documentation

## CSRF Exemptions

This document provides a comprehensive overview of all Cross-Site Request Forgery (CSRF) exemptions in the Derakht backend application, explaining why each exemption is necessary and what security measures are in place.

### Overview

CSRF protection is a critical security feature that prevents unauthorized commands from being transmitted from a user's browser that the web application trusts. However, certain endpoints in this application are exempt from CSRF protection for legitimate architectural and technical reasons.

### General Principles

**When CSRF Protection is NOT Needed:**
1. **JWT-authenticated API endpoints**: Modern REST APIs using stateless JWT authentication in the `Authorization` header do not need CSRF protection because they don't rely on browser cookies for authentication
2. **Public endpoints with no session state**: Endpoints accessed by unauthenticated users with no existing session to protect
3. **External system callbacks**: Endpoints designed to receive callbacks from external services (e.g., payment gateways) where requests originate from external servers, not user browsers

### CSRF Exempt Endpoints

#### 1. Payment Gateway Callback

**Location**: `shop/views/payment.py:170`
**Class**: `PaymentCallbackView`
**Method**: GET

**Reason for Exemption**:
- This is a callback endpoint for external payment gateways (Zarinpal)
- Requests originate from the payment gateway's servers, not user browsers
- No browser cookies or session data involved in verification

**Security Measures**:
- Payment verification with gateway using authority token
- Payment status validation prevents duplicate processing
- Payment amount validation ensures it matches order total
- Comprehensive logging of all callback attempts with IP addresses
- Payment ID validation (must exist in database)
- Order status checks prevent replay attacks

**Risk Level**: Low

---

#### 2. User Registration

**Location**: `users/views.py:248`
**Class**: `SignUpView`
**Method**: POST

**Reason for Exemption**:
- Public registration endpoint for unauthenticated users
- No existing session or authenticated state to protect
- Registration forms accessed cross-origin from frontend
- CSRF protection designed for authenticated sessions, not public endpoints

**Security Measures**:
- Email uniqueness validation prevents duplicate accounts
- Email verification token generation for account activation
- Password validation (Django's built-in strength requirements)
- Comprehensive input validation via `SignUpSerializer`
- No automatic authentication after registration
- All registration attempts logged for audit trail

**Risk Level**: Low
**TODO**: Implement rate limiting to prevent abuse and account enumeration

---

#### 3. Story API Endpoints

All story-related endpoints use JWT authentication and are exempt from CSRF for the same architectural reason: they are stateless REST API endpoints.

##### 3.1 Upload Story Cover

**Location**: `stories/views.py:399`
**Class**: `StoryViewSet`
**Action**: `upload_cover`
**Method**: POST

**Reason for Exemption**:
- JWT-authenticated API endpoint
- Authentication via `Authorization` header (Bearer token), not cookies
- Modern API pattern using stateless authentication

**Security Measures**:
- Valid JWT token required (`IsAuthenticated`)
- User can only upload cover for their own stories (ownership check)
- File type validation via serializer
- File size limits enforced by `MultiPartParser` configuration
- Comprehensive logging of all upload attempts

---

##### 3.2 Set Story Configuration

**Location**: `stories/views.py:473`
**Class**: `StoryViewSet`
**Action**: `set_config`
**Method**: POST

**Reason for Exemption**:
- JWT-authenticated API endpoint
- Stateless authentication via Bearer token

**Security Measures**:
- JWT authentication required
- Ownership verification (user can only modify own stories)
- Input validation via model validators (`full_clean()`)
- Color format validation for hex color codes

---

##### 3.3 Add Story Part

**Location**: `stories/views.py:512`
**Class**: `StoryViewSet`
**Action**: `add_part`
**Method**: POST

**Reason for Exemption**:
- JWT-based API endpoint
- Bearer token authentication, not session cookies
- RESTful API consumed by frontend SPA

**Security Measures**:
- Authentication required via JWT token
- User ownership validation
- Template validation (story_part_template must belong to story's template)
- Canvas data validation via model fields
- Activity type validation ensures proper story workflow

---

##### 3.4 Update Story Title

**Location**: `stories/views.py:612`
**Class**: `StoryViewSet`
**Action**: `update_title`
**Method**: PATCH

**Reason for Exemption**:
- JWT-authenticated API endpoint
- Stateless authentication via `Authorization` header
- No cookie-based session state

**Security Measures**:
- JWT token required
- Ownership check via `get_object()`
- Input validation (title required, non-empty)

---

##### 3.5 Finish Story

**Location**: `stories/views.py:641`
**Class**: `StoryViewSet`
**Action**: `finish`
**Method**: POST

**Reason for Exemption**:
- JWT-authenticated REST API endpoint
- Token-based authentication, not cookies
- Stateless architecture pattern

**Security Measures**:
- JWT authentication required
- User can only finish their own stories
- Status transition validation (from IN_PROGRESS to COMPLETED)
- Comprehensive logging of completion events

---

##### 3.6 Reset Story Part

**Location**: `stories/views.py:786`
**Class**: `StoryPartViewSet`
**Action**: `reset`
**Method**: POST

**Reason for Exemption**:
- JWT-authenticated API endpoint
- Stateless token authentication in `Authorization` header
- RESTful API consumed by SPA frontend

**Security Measures**:
- JWT token authentication required
- Ownership validation (user can only reset own story parts)
- Template association validation
- Comprehensive logging of reset operations

---

##### 3.7 Upload Story Part Image

**Location**: `stories/views.py:856`
**Class**: `StoryPartImageUploadView`
**Method**: POST

**Reason for Exemption**:
- JWT-authenticated API endpoint using Bearer token
- Stateless authentication - no session cookies
- Modern API pattern for file uploads from SPA frontend
- `MultiPartParser` handles file uploads which don't work well with CSRF tokens

**Security Measures**:
- JWT authentication required (`IsAuthenticated`)
- User ownership validation (can only upload to own story parts)
- File type validation via `StoryPartImageUploadSerializer`
- File size limits enforced by parser configuration
- Story part existence validation
- Comprehensive logging of all upload attempts
- Image validation ensures only valid formats accepted
- Uploaded files stored with UUID-based filenames preventing path traversal
- S3/MinIO storage with appropriate access controls
- All upload failures logged for security monitoring

---

## Security Best Practices

### Authentication Architecture

This application uses a hybrid authentication approach:

1. **JWT Tokens for API Endpoints**: All API endpoints use JWT (JSON Web Tokens) for stateless authentication. Tokens are passed in the `Authorization: Bearer <token>` header and do not require CSRF protection.

2. **Session-Based Auth for Admin**: Django admin and Wagtail CMS use traditional session-based authentication with full CSRF protection enabled.

### Verification Command

To audit all CSRF exemptions in the codebase:

```bash
# Find all CSRF exempt decorators
grep -rn "@method_decorator(csrf_exempt" --include="*.py" .

# Expected results:
# shop/views/payment.py:170
# users/views.py:248
# stories/views.py:399
# stories/views.py:473
# stories/views.py:512
# stories/views.py:612
# stories/views.py:641
# stories/views.py:786
# stories/views.py:856
```

### Recommendations

1. **Rate Limiting**: Implement rate limiting at the infrastructure level (nginx, load balancer) for all public endpoints, especially:
   - User registration (`/api/users/register/`)
   - Login endpoints (`/api/users/login/`)
   - Password reset endpoints

2. **Payment Gateway Signature Verification**: Add signature verification for payment gateway callbacks using Zarinpal's signature mechanism for an additional security layer.

3. **File Upload Limits**: Ensure file size and type restrictions are enforced at multiple levels:
   - Application level (Django settings)
   - Web server level (nginx/Apache)
   - Storage level (S3/MinIO policies)

4. **Monitoring**: Implement monitoring and alerting for:
   - Unusual registration patterns
   - Failed payment verifications
   - Excessive file upload attempts
   - JWT token abuse patterns

5. **API Versioning**: Consider implementing API versioning to allow for security updates without breaking existing clients.

---

## Related Documentation

- Django CSRF Documentation: https://docs.djangoproject.com/en/5.1/ref/csrf/
- JWT Security Best Practices: https://tools.ietf.org/html/rfc8725
- OWASP CSRF Prevention: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html

---

**Last Updated**: 2026-01-01
**Review Frequency**: Quarterly or after significant security-related changes
