from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    StoryViewSet,
    StoryTemplateViewSet,
    StoryCollectionViewSet,
    ImageAssetViewSet,
    StoryPartViewSet,
    StoryPartImageUploadView,
)

router = DefaultRouter()
router.register(r'templates', StoryTemplateViewSet)
router.register(r'collections', StoryCollectionViewSet)
router.register(r'images', ImageAssetViewSet, basename='image')
router.register(r'parts', StoryPartViewSet, basename='part')
router.register(r'', StoryViewSet, basename='story')

urlpatterns = [
    path('upload-part-image/', StoryPartImageUploadView.as_view(), name='upload-part-image'),
    path('', include(router.urls)),
]
