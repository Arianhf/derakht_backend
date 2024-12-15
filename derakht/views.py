from django.http import HttpResponse

def robots_txt(request):
    content = """User-agent: *
Allow: /
Sitemap: https://derrakht.ir/sitemap.xml

# Prevent crawling of admin pages
Disallow: /admin/
"""
    return HttpResponse(content, content_type="text/plain")