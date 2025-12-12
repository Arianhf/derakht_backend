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
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.contrib.sitemaps.views import sitemap
from wagtail.documents import urls as wagtaildocs_urls

from blog.urls import router
from derakht.views import robots_txt
from shop.urls import wagtail_api_router as shop_router

urlpatterns = [
    path("robots.txt", robots_txt),
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("api/users/", include("users.urls")),
    path("api/stories/", include("stories.urls")),
    path("api/blog/", router.urls),
    path("api/blog/", shop_router.urls),
    path("api/core/", include("core.urls")),
    path("api/shop/", include("shop.urls", namespace="shop")),
    path("", include("blog.urls")),
    path("sitemap.xml", sitemap),
    path("", include(wagtail_urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
