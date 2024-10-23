from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StoryViewSet, StoryCollectionViewSet

router = DefaultRouter()
router.register(r'stories', StoryViewSet)
router.register(r'collections', StoryCollectionViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]