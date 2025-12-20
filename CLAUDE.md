# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Derakht is a Django-based backend application combining a CMS (Wagtail), e-commerce platform, and creative storytelling features. The project is designed for an Iranian audience, supporting Persian content and Jalali calendar dates.

## Core Architecture

### Technology Stack
- **Framework**: Django 5.2+ with Python 3.12+
- **CMS**: Wagtail 6.4+ for content management
- **Database**: PostgreSQL 15
- **API**: Django REST Framework with JWT authentication
- **Storage**: MinIO (S3-compatible) for media/static files
- **Payment**: Zarinpal SDK integration

### Application Structure

The codebase follows a domain-based organization with four main Django apps:

1. **blog**: Wagtail-powered blog with SEO features, Jalali dates, and Persian content
   - Models: `BlogPost`, `BlogIndexPage`, `BlogCategory`
   - Uses Wagtail Page model architecture
   - Supports tags, categories, related posts, and featured/hero posts
   - Custom panels for Jalali date inputs

2. **shop**: Full e-commerce system with cart, orders, payments, and inventory
   - Models organized in `/shop/models/`: `Product`, `Order`, `Cart`, `Payment`, `Category`, `PromoCode`
   - Views organized in `/shop/views/`: cart, order, payment, product
   - Payment gateway abstraction in `/shop/gateways/`
   - Uses Wagtail API router for product API endpoints

3. **stories**: Creative storytelling platform with templates and canvas-based composition
   - Models: `Story`, `StoryPart`, `StoryTemplate`, `StoryPartTemplate`, `ImageAsset`
   - Supports multiple activity types: WRITE_FOR_DRAWING, ILLUSTRATE, COMPLETE_STORY
   - Canvas data stored as JSONField for drawing/illustration features
   - Custom CSRF exemption middleware for story endpoints

4. **users**: Custom user authentication with profile management
   - Custom `User` model (extends AbstractUser) with email as USERNAME_FIELD
   - Iranian phone number validation (PhoneNumberField)
   - Address management with default address logic
   - JWT-based authentication via SimpleJWT

5. **core**: Cross-application utilities and feature flags
   - `FeatureFlag` model for controlling feature availability
   - Global search endpoint with PostgreSQL trigram similarity across blogs and products
   - Utility functions in `core/utils.py`

### Settings Architecture

The main settings file is `derakht/settings.py` with support for environment variable configuration:
- Database credentials via `POSTGRES_*` env vars
- MinIO storage via `MINIO_*` env vars
- Email via `EMAIL_*` env vars
- Zarinpal payment via `ZARINPAL_*` env vars
- Optional local overrides via `derakht/local_settings.py` (not in git)

### URL Structure

All API endpoints are prefixed with `/api/`:
- `/api/users/` - User authentication and profile management
- `/api/stories/` - Story creation and management
- `/api/blog/` - Blog and product API endpoints (shared router)
- `/api/core/` - Feature flags and global search
- `/api/shop/` - Shop cart, orders, and payment endpoints
- `/admin/` - Wagtail admin interface
- `/django-admin/` - Django admin interface

## Development Commands

### Local Development (Docker)
```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up

# Run without Docker (requires PostgreSQL and MinIO)
python manage.py runserver
```

### Database Operations
```bash
# Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Testing
```bash
# Run all tests
pytest

# Run tests for specific app
pytest blog/tests.py
pytest shop/tests.py
pytest stories/tests.py
pytest users/tests.py
```

### Data Management
```bash
# Initialize feature flags
python manage.py init_feature_flags

# Collect static files (for production)
python manage.py collectstatic --noinput
```

### Code Quality
```bash
# Format code with black
black .

# Check formatting
black --check .
```

## Important Patterns

### Persian/Jalali Date Handling
- Blog posts use `jdatetime` for Jalali calendar support
- Custom template tags in `blog/templatetags/jalali_tags.py`
- Custom Wagtail panel `JalaliDatePanel` for admin interface

### Storage Strategy
- MinIO S3-compatible storage for all media and static files
- Custom storage backends in `blog/storages.py`:
  - `MediaStorage` for user uploads (bucket: media)
  - `StaticStorage` for static files (bucket: static)
- Files are never overwritten (`AWS_S3_FILE_OVERWRITE = False`)

### Authentication Flow
- JWT tokens with rotation and blacklisting enabled
- Access token lifetime: 60 minutes
- Refresh token lifetime: 7 days
- User verification via email tokens (`email_verification_token` field)

### Payment Processing
- Gateway abstraction pattern in `shop/gateways/`
- Currently supports Zarinpal SDK
- Payment flow: Order → Payment → PaymentTransaction → Verification
- Callback URL handling for payment gateway redirects

### Wagtail Integration
- Blog uses Wagtail Page models for hierarchical content
- Shop products use Wagtail API but not Page models
- Custom Wagtail hooks in `*_app/wagtail_hooks.py` files
- Sitemap generation via `wagtail.contrib.sitemaps`

### CORS Configuration
- Currently set to `CORS_ALLOW_ALL_ORIGINS = True` (development)
- Custom header: `x-anonymous-cart-id` for guest cart sessions
- CSRF exemption for story endpoints via custom middleware

## Key Constraints

### Phone Number Validation
- Only Iranian mobile numbers accepted by default (country code +98)
- Must start with 9 and be 10 digits long
- Validation in `User.clean()` method

### Order Processing
- Orders have distinct states managed in `shop/order_management.py`
- Payment must be verified before order completion
- Stock management on order completion

### Story Canvas Data
- Canvas data stored as JSONField (PostgreSQL JSONB)
- Used for drawing/illustration features in story parts
- Validation happens at application level, not database level

### Default Address Logic
- Each user can have one default address
- Setting an address as default automatically unsets others
- First address for a user is automatically set as default

## Production Deployment

The project uses Docker Compose with:
- Gunicorn WSGI server (4 workers)
- Nginx reverse proxy
- PostgreSQL 15 database
- Persistent volumes for database, static files, and media

Environment variables required for production (see `.env` file):
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=0`
- `DJANGO_ALLOWED_HOSTS`
- `POSTGRES_*` credentials
- `MINIO_*` configuration
- `EMAIL_*` settings
- `ZARINPAL_*` credentials
- `CSRF_TRUSTED_ORIGINS`

## Common Gotchas

1. **Wagtail vs Django Admin**: Blog content is managed through Wagtail admin at `/admin/`, while other models use Django admin at `/django-admin/`

2. **Custom User Model**: Always use `settings.AUTH_USER_MODEL` in foreign keys, never reference `users.User` directly

3. **Storage URLs**: Media/static URLs are constructed from MinIO endpoint, ensure `MINIO_EXTERNAL_API` is set correctly for public access

4. **Migration Dependencies**: Stories and shop apps may have dependencies on users app due to foreign keys

5. **Test Data**: No fixtures provided; use `init_feature_flags` command for initial feature flag setup
