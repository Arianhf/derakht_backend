from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StoryViewSet, StoryTemplateViewSet, StoryCollectionViewSet

router = DefaultRouter()
router.register(r'templates', StoryTemplateViewSet)
router.register(r'stories', StoryViewSet)
router.register(r'collections', StoryCollectionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]