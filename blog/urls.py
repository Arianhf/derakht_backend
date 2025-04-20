from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import PagesAPIViewSet
from wagtail.images.api.v2.views import ImagesAPIViewSet
from django.urls import path
from blog.views import related_posts

from blog.views import (
    BlogPostAPIViewSet,
    BlogIndexPageAPIViewSet,
    BlogCategoryAPIViewSet,
)

router = WagtailAPIRouter("blog")

router.register_endpoint("pages", PagesAPIViewSet)
router.register_endpoint("posts", BlogPostAPIViewSet)
router.register_endpoint("index", BlogIndexPageAPIViewSet)
router.register_endpoint("images", ImagesAPIViewSet)
router.register_endpoint("categories", BlogCategoryAPIViewSet)


urlpatterns = [
    path("api/v2/related-posts/<str:post_id>/", related_posts, name="related_posts"),
]
