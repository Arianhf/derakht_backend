# Global Search API

## Overview
The global search API provides fuzzy search capabilities across blogs and products using PostgreSQL trigram similarity. This allows you to search all content on your website with a single endpoint and get relevant results even with typos or partial matches.

## Endpoint
```
GET /api/v2/search/
```

## Features
- **Fuzzy Search**: Uses PostgreSQL trigram similarity for flexible matching (handles typos, partial matches)
- **Multi-model Search**: Searches both blog posts and products simultaneously
- **Relevance Scoring**: Results are ordered by similarity/relevance score
- **Pagination**: Supports pagination for large result sets
- **Configurable Threshold**: Adjust minimum similarity threshold for results

## Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | Yes | - | Search query text |
| `threshold` | float | No | 0.1 | Minimum similarity score (0.0-1.0). Lower = more results |
| `page` | integer | No | 1 | Page number for pagination |
| `page_size` | integer | No | 10 | Results per page (max 50) |

## Response Format

### Success Response (200 OK)
```json
{
  "count": 25,
  "next": "http://example.com/api/v2/search/?page=2&q=toy",
  "previous": null,
  "results": {
    "query": "toy",
    "threshold": 0.1,
    "total_results": 25,
    "blog_count": 10,
    "product_count": 15,
    "results": [
      {
        "id": 123,
        "type": "product",
        "title": "Wooden Toy Car",
        "description": "A beautiful handcrafted wooden toy car for children",
        "slug": "wooden-toy-car",
        "price": "150000",
        "sku": "TOY-001",
        "similarity": 0.856,
        "stock": 10,
        "is_available": true,
        "url": "/shop/products/wooden-toy-car/"
      },
      {
        "id": 456,
        "type": "blog",
        "title": "Best Toys for 5 Year Olds",
        "subtitle": "A comprehensive guide",
        "description": "Discover the best educational toys...",
        "slug": "best-toys-for-5-year-olds",
        "date": "2025-11-01",
        "similarity": 0.743,
        "featured": false,
        "hero": false,
        "reading_time": 5,
        "url": "/blog/best-toys-for-5-year-olds/"
      }
    ]
  }
}
```

### Error Response (400 Bad Request)
```json
{
  "error": "Search query parameter \"q\" is required"
}
```

## Result Object Fields

### Blog Results
- `id`: Blog post ID
- `type`: Always "blog"
- `title`: Blog post title
- `subtitle`: Blog post subtitle
- `description`: Intro/excerpt text
- `slug`: URL slug
- `date`: Publication date (YYYY-MM-DD)
- `similarity`: Relevance score (0.0-1.0)
- `featured`: Boolean - if post is featured
- `hero`: Boolean - if post is hero post
- `reading_time`: Estimated reading time in minutes
- `url`: Relative URL to blog post

### Product Results
- `id`: Product ID (UUID)
- `type`: Always "product"
- `title`: Product title
- `description`: Product description
- `slug`: URL slug
- `price`: Product price as string
- `sku`: Stock keeping unit
- `similarity`: Relevance score (0.0-1.0)
- `stock`: Available stock quantity
- `is_available`: Boolean - if product is available
- `url`: Relative URL to product

## Search Fields

### Blogs
The search looks in:
- Title
- Subtitle
- Intro/Description

### Products
The search looks in:
- Title
- Description
- SKU

## Usage Examples

### Basic Search
```bash
curl "http://localhost:8000/api/v2/search/?q=wooden"
```

### Search with Custom Threshold
```bash
# Stricter matching (only very similar results)
curl "http://localhost:8000/api/v2/search/?q=wooden&threshold=0.3"

# Looser matching (more results, including fuzzy matches)
curl "http://localhost:8000/api/v2/search/?q=wooden&threshold=0.05"
```

### Paginated Search
```bash
curl "http://localhost:8000/api/v2/search/?q=toy&page=2&page_size=20"
```

### Fuzzy Search Examples
```bash
# Will find "wooden" even with typo
curl "http://localhost:8000/api/v2/search/?q=woden"

# Partial match
curl "http://localhost:8000/api/v2/search/?q=wood"
```

## Implementation Details

### Database Setup
The search uses PostgreSQL's `pg_trgm` extension for trigram similarity matching. To enable this:

1. Run migrations:
```bash
python manage.py migrate
```

This will enable the `pg_trgm` extension in your PostgreSQL database.

### How Trigram Similarity Works
- Breaks text into 3-character sequences (trigrams)
- Compares trigrams between search query and database fields
- Returns similarity score (0.0 = no match, 1.0 = perfect match)
- Excellent for fuzzy matching, typos, and partial matches

### Performance Considerations
- Results are sorted by relevance in-memory after database queries
- For better performance with large datasets, consider:
  - Adding database indexes on searched fields
  - Using GIN indexes on trigram fields
  - Implementing search result caching
  - Using a dedicated search engine (Elasticsearch) for very large datasets

### Threshold Recommendations
- `0.05-0.15`: Very loose matching (good for general search)
- `0.2-0.3`: Moderate matching (balanced)
- `0.4+`: Strict matching (very similar terms only)

## Integration with Frontend

### React/Next.js Example
```javascript
async function searchWebsite(query) {
  const response = await fetch(
    `/api/v2/search/?q=${encodeURIComponent(query)}`
  );
  const data = await response.json();
  return data.results;
}

// Usage
const results = await searchWebsite("wooden toy");
console.log(`Found ${results.total_results} results`);
console.log(`Blogs: ${results.blog_count}, Products: ${results.product_count}`);
```

### Search Box Component Example
```javascript
function SearchBox() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);

  const handleSearch = async (e) => {
    e.preventDefault();
    const response = await fetch(`/api/v2/search/?q=${query}`);
    const data = await response.json();
    setResults(data.results.results);
  };

  return (
    <form onSubmit={handleSearch}>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search blogs and products..."
      />
      <button type="submit">Search</button>

      {results.map(item => (
        <div key={`${item.type}-${item.id}`}>
          <h3>{item.title}</h3>
          <p>{item.description}</p>
          <a href={item.url}>View {item.type}</a>
          <span>Relevance: {(item.similarity * 100).toFixed(0)}%</span>
        </div>
      ))}
    </form>
  );
}
```

## Testing

### Manual Testing
1. Start your Django server
2. Open browser or use curl
3. Test with various queries:
   - Exact matches
   - Typos
   - Partial words
   - Different thresholds

### Automated Testing
Example test case:
```python
from django.test import TestCase
from django.urls import reverse

class GlobalSearchTestCase(TestCase):
    def test_search_requires_query(self):
        response = self.client.get(reverse('global-search'))
        self.assertEqual(response.status_code, 400)

    def test_search_returns_results(self):
        response = self.client.get(reverse('global-search'), {'q': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
```

## Future Enhancements
- Add filters (by date, price range, category)
- Include product images in results
- Add autocomplete/suggestions endpoint
- Support for advanced search operators
- Search history and popular searches
- Highlighting of matched terms
- Support for multiple languages
