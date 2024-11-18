"""
URL configuration for derakht project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

def list_urls(urlpatterns, indent=0):
    """Recursively print all URL patterns with their view names and paths."""
    urls = []
    for pattern in urlpatterns:
        if isinstance(pattern, URLPattern):
            # It's a URL pattern
            urls.append({
                'pattern': str(pattern.pattern),
                'name': pattern.name,
                'view': pattern.callback.__name__ if hasattr(pattern.callback, '__name__') else str(pattern.callback),
                'indent': indent
            })
        elif isinstance(pattern, URLResolver):
            # It's an included URLconf
            urls.append({
                'pattern': str(pattern.pattern),
                'namespace': pattern.namespace,
                'app_name': pattern.app_name,
                'indent': indent
            })
            urls.extend(list_urls(pattern.url_patterns, indent + 1))
    return urls

# You can create a view to display this:
from django.http import JsonResponse

def show_urls(request):
    """View to display all URLs in the project."""
    resolver = get_resolver()
    urls = list_urls(resolver.url_patterns)
    return JsonResponse({'urls': urls})

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('admin/', include(wagtailadmin_urls)),
    path('documents/', include(wagtaildocs_urls)),
    path('api/users/', include('users.urls')),
    path('api/stories/', include('stories.urls')),
    path('debug/urls/', show_urls, name='show_urls'),
    path('', include(wagtail_urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


