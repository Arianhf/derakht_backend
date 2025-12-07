# Story Orientation & Size API Specification

## Overview
Stories now support orientation and size fields that can be set by admins to control story display formatting.

## New Fields

### `orientation` (optional)
- **Type**: String
- **Allowed Values**:
  - `"LANDSCAPE"` - Landscape orientation
  - `"PORTRAIT"` - Portrait orientation
  - `null` - No orientation set
- **Description**: Specifies whether the story should be displayed in landscape or portrait mode

### `size` (optional)
- **Type**: String
- **Allowed Values**:
  - `"20x20"` - 20x20 size
  - `"25x25"` - 25x25 size
  - `"15x23"` - 15x23 size
  - `null` - No size set
- **Description**: Specifies the rectangular size dimensions for the story

## API Endpoints Affected

All story-related endpoints now include these fields:

### GET `/api/stories/` - List User's Stories
### GET `/api/stories/{id}/` - Get Story Details
### GET `/api/stories/completed/` - List Completed Stories

**Response Example:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "My Story",
  "author": {
    "id": "uuid",
    "username": "john_doe",
    "profile_image": "http://example.com/media/profiles/image.jpg"
  },
  "created_date": "2025-12-07T10:35:00Z",
  "activity_type": "WRITE_FOR_DRAWING",
  "status": "DRAFT",
  "story_template": "uuid-or-null",
  "parts": [...],
  "cover_image": "http://example.com/media/stories/covers/image.jpg",
  "background_color": "#FF5733",
  "font_color": "#000000",
  "orientation": "LANDSCAPE",
  "size": "25x25"
}
```

### POST `/api/stories/` - Create Story

**Request Body:**
```json
{
  "title": "New Story",
  "orientation": "PORTRAIT",
  "size": "20x20"
}
```

**Note**: Only `title` is required. `orientation` and `size` are optional.

### PUT `/api/stories/{id}/` - Update Story
### PATCH `/api/stories/{id}/` - Partial Update Story

**Request Body Example:**
```json
{
  "orientation": "LANDSCAPE",
  "size": "15x23"
}
```

## Validation Rules

1. **orientation** must be one of: `"LANDSCAPE"`, `"PORTRAIT"`, or `null`
2. **size** must be one of: `"20x20"`, `"25x25"`, `"15x23"`, or `null`
3. Both fields are **optional** - you can omit them or set them to `null`
4. Invalid values will return a `400 Bad Request` error

## Error Responses

### Invalid Orientation Value
```json
{
  "orientation": [
    "\"HORIZONTAL\" is not a valid choice."
  ]
}
```

### Invalid Size Value
```json
{
  "size": [
    "\"30x30\" is not a valid choice."
  ]
}
```

## Frontend Implementation Guidelines

### Display Logic
```javascript
// Example: Determine CSS class based on orientation
const getOrientationClass = (story) => {
  if (story.orientation === 'LANDSCAPE') return 'story-landscape';
  if (story.orientation === 'PORTRAIT') return 'story-portrait';
  return 'story-default';
};

// Example: Get size dimensions
const getSizeDimensions = (story) => {
  const sizes = {
    '20x20': { width: 20, height: 20 },
    '25x25': { width: 25, height: 25 },
    '15x23': { width: 15, height: 23 }
  };
  return sizes[story.size] || { width: 'auto', height: 'auto' };
};
```

### Filtering/Grouping
You can filter or group stories by orientation and size on the frontend:
```javascript
const landscapeStories = stories.filter(s => s.orientation === 'LANDSCAPE');
const size20x20Stories = stories.filter(s => s.size === '20x20');
```

## TypeScript Types

```typescript
type StoryOrientation = 'LANDSCAPE' | 'PORTRAIT' | null;
type StorySize = '20x20' | '25x25' | '15x23' | null;

interface Story {
  id: string;
  title: string;
  author: {
    id: string;
    username: string;
    profile_image: string | null;
  };
  created_date: string;
  activity_type: 'WRITE_FOR_DRAWING' | 'ILLUSTRATE' | 'COMPLETE_STORY';
  status: 'DRAFT' | 'COMPLETED';
  story_template: string | null;
  parts: StoryPart[];
  cover_image: string | null;
  background_color: string | null;
  font_color: string | null;
  orientation: StoryOrientation;  // NEW
  size: StorySize;                 // NEW
}
```

## Migration Notes

- Existing stories will have `orientation` and `size` set to `null`
- These fields are **admin-controlled** - admins set them via Django admin panel
- Frontend should handle `null` values gracefully (use default display settings)

## Questions?

Contact the backend team if you have any questions about these new fields.
