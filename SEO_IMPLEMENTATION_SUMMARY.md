# Blog SEO API Implementation Summary

## Overview
This document summarizes the backend API changes implemented for comprehensive SEO optimization of the Derakht blog platform.

## Changes Implemented

### 1. BlogPost Model Enhancements (`blog/models.py`)

#### New SEO Fields Added:
1. **`meta_title`** (CharField, 200 chars, optional)
   - Custom SEO title for search results
   - Falls back to page title if not provided
   - Recommended: 50-60 characters

2. **`meta_description`** (TextField, optional)
   - SEO description for search results
   - Recommended: 150-160 characters

3. **`excerpt`** (TextField, optional)
   - Short summary for post previews
   - Different from meta_description (more conversational)
   - Recommended: 150-200 characters

4. **`word_count`** (PositiveIntegerField, default=0)
   - Auto-calculated from body content
   - Calculated in the `save()` method

5. **`canonical_url`** (URLField, 500 chars, optional)
   - Canonical URL if content exists elsewhere

6. **`og_image`** (ForeignKey to Image, optional)
   - Custom Open Graph image for social sharing
   - Falls back to header_image if not provided

7. **`featured_snippet`** (TextField, optional)
   - Optimized content for Google featured snippets
   - Recommended: 40-60 words

8. **`noindex`** (BooleanField, default=False)
   - Prevent search engines from indexing this post

#### New Properties Added:
1. **`published_date`** (property)
   - Returns ISO 8601 format timestamp (e.g., "2024-01-15T00:00:00Z")
   - Converts the existing `date` field to ISO format

2. **`updated_date`** (property)
   - Returns ISO 8601 format timestamp of last modification
   - Only returns if post was modified after initial publication
   - Uses Wagtail's `last_published_at` field

3. **`calculate_word_count()`** (method)
   - Strips HTML tags from rich text body
   - Counts words in plain text

#### Updated Methods:
- **`save()`** - Now auto-calculates word_count before saving

#### Admin Panel Updates:
- Added new "SEO Settings" collapsible panel in the admin
- Includes all new SEO fields in the content_panels

#### API Fields:
All new fields are exposed via the API through the `api_fields` list.

---

### 2. BlogCategory Model Enhancements (`blog/models.py`)

#### New SEO Fields Added:
1. **`meta_title`** (CharField, 200 chars, optional)
   - SEO title for category page
   - Recommended: 50-60 characters

2. **`meta_description`** (TextField, optional)
   - SEO description for category page
   - Recommended: 150-160 characters

#### Admin Panel Updates:
- Both meta fields added to the admin panels

---

### 3. User Model Enhancements (`users/models.py`)

#### New Author/SEO Fields Added:
1. **`bio`** (TextField, optional)
   - Short author biography
   - Recommended: 100-200 characters

2. **`social_links`** (JSONField, default=dict)
   - Stores social media links as JSON
   - Format: `{"twitter": "url", "instagram": "url", "linkedin": "url"}`

#### New Methods Added:
- **`get_profile_url()`** - Generates URL to author's profile page
  - Format: `/authors/{first-name}-{last-name}`
  - Uses Django's slugify with Unicode support

---

### 4. Enhanced Serializers

#### SmallUserSerializer (`users/serializers.py`)
**Updated to include:**
- `id` - User ID
- `first_name` - First name
- `last_name` - Last name
- `full_name` - Computed full name (via get_full_name())
- `age` - User age
- `profile_image` - Profile image URL
- `bio` - Author biography
- `profile_url` - URL to author profile page (computed)
- `email` - Author email
- `social_links` - Social media links JSON

#### BlogCategorySerializer (`blog/category_serializer.py`)
**Updated to include:**
- `meta_title` - SEO title
- `meta_description` - SEO description
- (All existing fields retained)

---

### 5. API View Enhancements (`blog/views.py`)

#### BlogPostAPIViewSet Updates:

1. **Enhanced `listing_default_fields`**
   - Added: `excerpt`, `published_date`, `updated_date`, `word_count`
   - Added: `meta_title`, `meta_description`

2. **New `detail_view()` method** (overrides parent)
   - Supports both ID and slug-based retrieval
   - Auto-detects numeric ID vs string slug
   - Examples:
     - `GET /api/v2/posts/123/` (ID-based, backward compatible)
     - `GET /api/v2/posts/آموزش-ریاضی-کودکان/` (slug-based, new)

3. **New `slugs()` action** (`@action` decorator)
   - Endpoint: `GET /api/v2/posts/slugs/`
   - Returns all published post slugs with updated dates
   - Optimized with `.only()` for performance
   - Response format:
     ```json
     {
       "items": [
         {
           "slug": "post-slug",
           "updated_date": "2024-01-15T10:30:00Z"
         }
       ],
       "total": 50
     }
     ```
   - Use case: Sitemap generation

4. **Updated URL patterns** (`get_urlpatterns()`)
   - Added: `path("slugs/", ...)` for slug list endpoint
   - Added: `path("<str:pk>/", ...)` for slug-based detail view
   - Maintains backward compatibility with ID-based URLs

---

### 6. Database Migrations

#### Blog App Migration (`blog/migrations/0009_add_seo_fields.py`)
- Adds all 8 new SEO fields to BlogPost model
- Adds 2 meta fields to BlogCategory model
- Safe to run (all fields are optional/have defaults)

#### Users App Migration (`users/migrations/0004_add_author_seo_fields.py`)
- Adds `bio` field to User model
- Adds `social_links` JSONField to User model
- Safe to run (all fields have defaults)

---

## API Response Examples

### Complete BlogPost Response
```json
{
  "id": 1,
  "slug": "آموزش-ریاضی-کودکان",
  "title": "آموزش ریاضی به کودکان",
  "subtitle": "روش‌های جذاب و سرگرم‌کننده",
  "intro": "ریاضی یکی از مهم‌ترین مهارت‌های زندگی است...",
  "excerpt": "در این مقاله با روش‌های جذاب آموزش ریاضی به کودکان آشنا می‌شوید...",
  "meta_title": "آموزش ریاضی به کودکان | بهترین روش‌های یادگیری 2024",
  "meta_description": "آموزش ریاضی به کودکان با روش‌های سرگرم‌کننده و بازی‌های تعاملی...",
  "body": "<p>محتوای کامل مقاله...</p>",
  "header_image": {
    "meta": {
      "download_url": "https://..."
    }
  },
  "og_image": {
    "meta": {
      "download_url": "https://..."
    }
  },
  "categories": [...],
  "owner": {
    "id": 123,
    "first_name": "سارا",
    "last_name": "محمدی",
    "full_name": "سارا محمدی",
    "bio": "نویسنده و مربی کودک با ۱۰ سال تجربه...",
    "profile_url": "/authors/sara-mohammadi",
    "profile_image": "https://...",
    "email": "sara@example.com",
    "social_links": {
      "twitter": "https://twitter.com/sara_mohammadi",
      "instagram": "https://instagram.com/sara_mohammadi"
    },
    "age": 35
  },
  "tags": ["آموزش ریاضی", "کودکان"],
  "jalali_date": "1403-10-25",
  "published_date": "2024-01-15T00:00:00Z",
  "updated_date": "2024-02-20T15:45:00Z",
  "reading_time": 8,
  "word_count": 1250,
  "featured": true,
  "hero": false,
  "alternative_titles": ["ریاضی برای کودکان"],
  "canonical_url": "https://derakht.com/blog/آموزش-ریاضی-کودکان",
  "featured_snippet": "بهترین روش آموزش ریاضی به کودکان استفاده از بازی‌های آموزشی است...",
  "noindex": false
}
```

### Enhanced Category Response
```json
{
  "id": 5,
  "name": "آموزش ریاضی",
  "slug": "math-education",
  "description": "مقالات آموزشی ریاضی برای کودکان",
  "icon": "https://...",
  "post_count": 15,
  "meta_title": "مقالات آموزش ریاضی برای کودکان | درخت",
  "meta_description": "مجموعه کامل مقالات آموزش ریاضی"
}
```

### Slugs Endpoint Response
```json
{
  "items": [
    {
      "slug": "آموزش-ریاضی-کودکان",
      "updated_date": "2024-02-20T15:45:00Z"
    },
    {
      "slug": "داستان-کودکان",
      "updated_date": "2024-01-10T08:20:00Z"
    }
  ],
  "total": 50
}
```

---

## Available API Endpoints

### BlogPost Endpoints
1. **List posts**: `GET /api/v2/posts/`
2. **Get by ID**: `GET /api/v2/posts/{id}/`
3. **Get by slug**: `GET /api/v2/posts/{slug}/` ⭐ NEW
4. **Get slugs**: `GET /api/v2/posts/slugs/` ⭐ NEW
5. **Featured posts**: `GET /api/v2/posts/featured/`
6. **Hero post**: `GET /api/v2/posts/hero/`
7. **By category**: `GET /api/v2/posts/by_category/?slug={category_slug}`
8. **Filter by category**: `GET /api/v2/posts/?category={category_slug}`
9. **Search**: `GET /api/v2/posts/?search={query}`
10. **Related posts**: `GET /api/v2/related-posts/{post_id}/`

### Category Endpoints
1. **List categories**: `GET /api/v2/categories/`
2. **Get category**: `GET /api/v2/categories/{id}/`

---

## Deployment Instructions

### 1. Apply Migrations
```bash
# Using Docker
docker-compose exec web python manage.py migrate blog
docker-compose exec web python manage.py migrate users

# Or locally
python manage.py migrate blog
python manage.py migrate users
```

### 2. Update Existing Posts (Optional)
After migration, you may want to:
- Calculate word_count for existing posts
- Add excerpts and meta descriptions to existing posts
- This can be done via Django admin or a data migration script

### 3. Testing Checklist
- [ ] Create new post with all new fields via admin
- [ ] Retrieve post by ID: `GET /api/v2/posts/1/`
- [ ] Retrieve post by slug: `GET /api/v2/posts/test-post/`
- [ ] Verify word_count auto-calculates on save
- [ ] Verify published_date and updated_date in ISO format
- [ ] Check slugs endpoint: `GET /api/v2/posts/slugs/`
- [ ] Verify enhanced author object in post response
- [ ] Verify category meta fields in category endpoint
- [ ] Test that slug-based retrieval works with Persian slugs

---

## Backward Compatibility

✅ **All changes are backward compatible:**
- All new fields are optional (blank=True or have defaults)
- Existing API endpoints continue to work
- ID-based post retrieval still works
- No breaking changes to existing serializers

---

## Files Modified

### Models
- `blog/models.py` - BlogPost and BlogCategory models
- `users/models.py` - User model

### Serializers
- `users/serializers.py` - SmallUserSerializer
- `blog/category_serializer.py` - BlogCategorySerializer

### Views
- `blog/views.py` - BlogPostAPIViewSet

### Migrations
- `blog/migrations/0009_add_seo_fields.py` - NEW
- `users/migrations/0004_add_author_seo_fields.py` - NEW

---

## Notes

1. **Word Count Auto-Calculation**: The `word_count` field is automatically calculated when a post is saved. It strips HTML tags from the rich text body and counts words.

2. **Published vs Updated Dates**:
   - `published_date` is derived from the `date` field
   - `updated_date` only appears if the post has been modified after initial publication

3. **Slug Support**: The slug field already existed in Wagtail's Page model. We've added API support for slug-based retrieval.

4. **Social Links Format**: Store as JSON object:
   ```json
   {
     "twitter": "https://twitter.com/username",
     "instagram": "https://instagram.com/username",
     "linkedin": "https://linkedin.com/in/username"
   }
   ```

5. **Profile URLs**: Auto-generated from user's full name using Django's slugify with Unicode support.

---

## Implementation Date
November 2, 2025

## Status
✅ Complete - Ready for deployment
