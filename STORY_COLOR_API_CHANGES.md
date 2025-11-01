# Story Color API Changes

## Summary

We've removed the `background_image` field from stories and added support for customizable colors instead. Stories can now have a `background_color` and `font_color` set using hex color codes.

## What Changed

### Removed
- ❌ `background_image` field
- ❌ `POST /stories/<id>/upload_background` endpoint

### Added
- ✅ `background_color` field (hex color code)
- ✅ `font_color` field (hex color code)
- ✅ `POST /stories/<id>/set_config` endpoint

## Story Response Format

When you fetch a story (GET `/stories/<id>/`), you'll now receive:

```json
{
  "id": "uuid",
  "title": "My Story",
  "author": "user_id",
  "created_date": "2025-11-01T10:30:00Z",
  "activity_type": "WRITE_FOR_DRAWING",
  "story_template": "template_id",
  "parts": [...],
  "cover_image": "https://example.com/media/stories/covers/image.jpg",
  "background_color": "#FF5733",
  "font_color": "#FFFFFF"
}
```

**Note:** Both `background_color` and `font_color` can be `null` if not set.

## New Endpoint: Set Story Config

### Endpoint
```
POST /stories/<story_id>/set_config
```

### Authentication
Required (user must be the story author)

### Request Body
```json
{
  "background_color": "#FF5733",
  "font_color": "#FFFFFF"
}
```

**Fields:**
- `background_color` (optional): Hex color code for story background
- `font_color` (optional): Hex color code for story text
- Both fields accept `null` or empty string `""` to clear the value

### Accepted Color Formats
- 6-digit hex: `#RRGGBB` (e.g., `#FF5733`, `#000000`, `#FFFFFF`)
- 3-digit hex: `#RGB` (e.g., `#FFF`, `#000`, `#F73`)
- Must include the `#` prefix

### Success Response
**Status:** `200 OK`

```json
{
  "id": "uuid",
  "title": "My Story",
  "author": "user_id",
  "created_date": "2025-11-01T10:30:00Z",
  "activity_type": "WRITE_FOR_DRAWING",
  "story_template": "template_id",
  "parts": [...],
  "cover_image": "https://example.com/media/stories/covers/image.jpg",
  "background_color": "#FF5733",
  "font_color": "#FFFFFF"
}
```

### Error Response
**Status:** `400 Bad Request`

```json
{
  "error": {
    "background_color": [
      "INVALID is not a valid hex color code. Use format #RRGGBB or #RGB"
    ]
  }
}
```

## Usage Examples

### Example 1: Set Both Colors
```javascript
const response = await fetch(`/stories/${storyId}/set_config`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    background_color: '#FF5733',
    font_color: '#FFFFFF'
  })
});

const story = await response.json();
```

### Example 2: Update Only Background Color
```javascript
const response = await fetch(`/stories/${storyId}/set_config`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    background_color: '#000000'
  })
});
```

### Example 3: Clear Colors
```javascript
const response = await fetch(`/stories/${storyId}/set_config`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    background_color: '',
    font_color: ''
  })
});
```

## Migration Notes

- All existing stories will have `background_color` and `font_color` set to `null` by default
- Any existing `background_image` data has been removed during the migration
- The `upload_background` endpoint is no longer available and will return 404

## Questions?

If you have any questions about these changes, please reach out to the backend team.
