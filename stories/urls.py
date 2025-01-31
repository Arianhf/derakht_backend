from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import StoryViewSet, StoryTemplateViewSet, StoryCollectionViewSet, ImageAssetViewSet

router = DefaultRouter()
router.register(r'', StoryViewSet, basename='story')
router.register(r'templates', StoryTemplateViewSet)
router.register(r'collections', StoryCollectionViewSet)
router.register(r'images', ImageAssetViewSet, basename='image')

urlpatterns = [
    path('', include(router.urls)),
]
